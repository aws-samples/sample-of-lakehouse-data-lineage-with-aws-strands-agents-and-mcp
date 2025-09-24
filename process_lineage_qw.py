#!/usr/bin/env python3
"""
EC2 Data Lineage Processing Script
Modified from Lambda to run on EC2, reading from local raw-data directory
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import hashlib

try:
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import get_credentials
    from botocore.session import Session
    import requests
except ImportError as e:
    print(f"Error: Missing required module - {e}")
    print("\nPlease install: python3 -m pip install boto3 requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'lineage_processor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EC2LineageProcessor:
    """EC2 Data Lineage Processor"""
    
    def __init__(self, raw_data_path: str, neptune_endpoint: str, aws_region: str = 'us-east-1'):
        self.raw_data_path = Path(raw_data_path)
        self.neptune_endpoint = neptune_endpoint
        self.aws_region = aws_region
        
        logger.info("="*60)
        logger.info("EC2 Data Lineage Processor")
        logger.info("="*60)
        logger.info(f"  Data path: {self.raw_data_path}")
        logger.info(f"  Neptune endpoint: {self.neptune_endpoint}")
        logger.info(f"  AWS region: {self.aws_region}")
        logger.info("="*60)
    
    def process_lineage(self):
        """Main processing function"""
        try:
            # Read local JSON files
            glue_data = self._read_local_json('glue_lineage_map.json')
            redshift_data = self._read_local_json('redshift_lineage_map.json')
            
            if not glue_data or not redshift_data:
                logger.error("Failed to read lineage data from local files")
                return False
            
            # Process lineage data
            processor = LineageProcessor(glue_data, redshift_data)
            merged_data = processor.process()
            
            # Write to Neptune
            neptune_writer = NeptuneWriter(self.neptune_endpoint, self.aws_region)
            stats = neptune_writer.write_enhanced_lineage(merged_data)
            
            logger.info(f"Processing completed successfully: {stats}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing lineage data: {str(e)}", exc_info=True)
            return False
    
    def _read_local_json(self, filename):
        """Read JSON file from local raw-data directory"""
        file_path = self.raw_data_path / filename
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully read {filename}")
            return data
        except Exception as e:
            logger.error(f"Error reading {filename}: {str(e)}")
            return None

class LineageProcessor:
    """Process and merge Glue and Redshift lineage data"""
    
    def __init__(self, glue_data, redshift_data):
        self.glue_data = glue_data
        self.redshift_data = redshift_data
        self.merged_lineage = {}
        self.dataset_metadata = {}
        self.column_metadata = {}
        self.column_lineage = defaultdict(list)
        
    def process(self):
        """Process and merge lineage data"""
        # Extract lineage relationships and schema
        glue_lineage = self.glue_data.get('lineage', {})
        redshift_lineage = self.redshift_data.get('lineage', {})
        
        # Extract column-level lineage
        glue_column_lineage = self.glue_data.get('column_lineage', {})
        redshift_column_lineage = self.redshift_data.get('column_lineage', {})
        
        logger.info(f"Processing {len(glue_lineage)} Glue nodes and {len(redshift_lineage)} Redshift nodes")
        
        # Process Glue data
        self._process_glue_data(glue_lineage, glue_column_lineage)
        
        # Process Redshift data
        self._process_redshift_data(redshift_lineage, redshift_column_lineage)
        
        # Standardize data types
        self._standardize_data_types()
        
        return {
            'lineage': self.merged_lineage,
            'datasets': self.dataset_metadata,
            'columns': self.column_metadata,
            'column_lineage': dict(self.column_lineage)
        }
    
    def _process_glue_data(self, lineage, column_lineage):
        """Process Glue lineage data"""
        for dataset, info in lineage.items():
            # Extract downstream relationships
            downstream = info.get('downstream', [])
            if dataset not in self.merged_lineage:
                self.merged_lineage[dataset] = []
            self.merged_lineage[dataset].extend(downstream)
            
            # Extract schema information
            schema = info.get('schema', {})
            if schema:
                self._extract_glue_metadata(dataset, schema)
        
        # Process column-level lineage
        for col_key, col_info in column_lineage.items():
            self.column_lineage[col_key] = col_info
    
    def _process_redshift_data(self, lineage, column_lineage):
        """Process Redshift lineage data"""
        for dataset, info in lineage.items():
            # Extract downstream relationships
            downstream = info.get('downstream', [])
            if dataset not in self.merged_lineage:
                self.merged_lineage[dataset] = []
            
            # Merge downstream, avoid duplicates
            for item in downstream:
                if item not in self.merged_lineage[dataset]:
                    self.merged_lineage[dataset].append(item)
            
            # Extract schema information
            schema = info.get('schema', {})
            if schema:
                self._extract_redshift_metadata(dataset, schema)
        
        # Process column-level lineage
        for col_key, col_info in column_lineage.items():
            if col_key not in self.column_lineage:
                self.column_lineage[col_key] = col_info
    
    def _extract_glue_metadata(self, dataset, schema):
        """Extract Glue schema metadata"""
        # Dataset-level metadata
        self.dataset_metadata[dataset] = {
            'source_system': 'glue',
            'dataset_type': self._determine_dataset_type(dataset),
            'format': schema.get('format', 'unknown'),
            'timestamp': schema.get('timestamp', ''),
            'source_type': schema.get('source', '')
        }
        
        # Column-level metadata
        fields = schema.get('fields', [])
        for field in fields:
            col_key = f"{dataset}.{field['name']}"
            self.column_metadata[col_key] = {
                'dataset': dataset,
                'column_name': field['name'],
                'data_type': field.get('type', 'unknown'),
                'source': 'glue'
            }
    
    def _extract_redshift_metadata(self, dataset, schema):
        """Extract Redshift schema metadata"""
        # Dataset-level metadata
        metadata = {
            'source_system': 'redshift',
            'dataset_type': self._determine_dataset_type(dataset),
            'database': schema.get('database', ''),
            'schema_name': schema.get('schema', ''),
            'table_name': schema.get('table', ''),
            'timestamp': schema.get('timestamp', ''),
            'source_type': schema.get('source', '')
        }
        
        # Add statistics
        stats = schema.get('statistics', {})
        if stats:
            metadata.update({
                'row_count': stats.get('row_count', 0),
                'size_mb': stats.get('size_mb', 0),
                'distribution_style': stats.get('distribution_style', ''),
                'sort_key': stats.get('sort_key', '')
            })
        
        # Merge or update dataset metadata
        if dataset in self.dataset_metadata:
            # If exists (from Glue), merge information
            existing = self.dataset_metadata[dataset]
            existing['source_system'] = 'glue,redshift'
            existing.update({k: v for k, v in metadata.items() if v})
        else:
            self.dataset_metadata[dataset] = metadata
        
        # Column-level metadata
        fields = schema.get('fields', [])
        for field in fields:
            col_key = f"{dataset}.{field['name']}"
            col_metadata = {
                'dataset': dataset,
                'column_name': field['name'],
                'data_type': field.get('type', 'unknown'),
                'max_length': field.get('max_length'),
                'precision': field.get('precision'),
                'scale': field.get('scale'),
                'nullable': field.get('nullable', True),
                'default': field.get('default'),
                'source': 'redshift'
            }
            
            if col_key in self.column_metadata:
                # Merge information
                existing = self.column_metadata[col_key]
                existing['source'] = 'both'
                existing.update({k: v for k, v in col_metadata.items() if v is not None})
            else:
                self.column_metadata[col_key] = col_metadata
    
    def _determine_dataset_type(self, dataset):
        """Determine dataset type"""
        if dataset.startswith('s3://'):
            return 's3'
        elif '.' in dataset:
            return 'table'
        else:
            return 'unknown'
    
    def _standardize_data_types(self):
        """Standardize data type names"""
        type_mapping = {
            'string': 'varchar',
            'long': 'bigint',
            'integer': 'int',
            'double': 'double precision',
            'character varying': 'varchar',
            'timestamp without time zone': 'timestamp'
        }
        
        for col_key, col_info in self.column_metadata.items():
            data_type = col_info.get('data_type', '').lower()
            if data_type in type_mapping:
                col_info['data_type'] = type_mapping[data_type]

class NeptuneWriter:
    """Neptune graph database writer"""
    
    def __init__(self, neptune_endpoint, aws_region='us-east-1'):
        self.endpoint = self._prepare_endpoint(neptune_endpoint)
        self.aws_region = aws_region
        self.stats = {
            'datasets_created': 0,
            'columns_created': 0,
            'lineage_edges': 0,
            'column_edges': 0
        }
    
    def _prepare_endpoint(self, neptune_env):
        """Prepare Neptune endpoint URL"""
        if 'https://' not in neptune_env:
            return f'https://{neptune_env}:8182/gremlin'
        return neptune_env
    
    def write_enhanced_lineage(self, data):
        """Write enhanced lineage data to Neptune"""
        logger.info(f"Writing enhanced lineage to Neptune: {self.endpoint}")
        
        # Clear database
        self._clear_database()
        
        # Write dataset nodes
        self._write_dataset_nodes(data['datasets'])
        
        # Write column nodes
        self._write_column_nodes(data['columns'])
        
        # Write table-level lineage relationships
        self._write_lineage_edges(data['lineage'])
        
        # Write column-level lineage relationships
        self._write_column_lineage(data['column_lineage'])
        
        logger.info(f"Neptune write completed: {self.stats}")
        return self.stats
    
    def _clear_database(self):
        """Clear Neptune database"""
        query = "g.V().drop()"
        self._execute_query(query)
        logger.info("Database cleared")
    
    def _write_dataset_nodes(self, datasets):
        """Write dataset nodes"""
        for dataset, metadata in datasets.items():
            escaped_name = self._escape_string(dataset)
            
            # Build properties string
            props = [
                f".property('node_name', '{escaped_name}')",
                f".property('source_system', '{metadata.get('source_system', 'unknown')}')",
                f".property('dataset_type', '{metadata.get('dataset_type', 'unknown')}')"
            ]
            
            # Add optional properties
            if metadata.get('database'):
                props.append(f".property('database', '{self._escape_string(metadata['database'])}')")
            if metadata.get('schema_name'):
                props.append(f".property('schema_name', '{self._escape_string(metadata['schema_name'])}')")
            if metadata.get('row_count') is not None:
                props.append(f".property('row_count', {metadata['row_count']})")
            if metadata.get('size_mb') is not None:
                props.append(f".property('size_mb', {metadata['size_mb']})")
            if metadata.get('format'):
                props.append(f".property('format', '{metadata['format']}')")
            
            props_str = ''.join(props)
            
            query = f"""
                g.V().has('dataset', 'node_name', '{escaped_name}')
                .fold()
                .coalesce(
                    unfold(),
                    addV('dataset'){props_str}
                )
            """
            
            self._execute_query(query)
            self.stats['datasets_created'] += 1
    
    def _write_column_nodes(self, columns):
        """Write column nodes and establish relationships with datasets"""
        # Group by dataset
        columns_by_dataset = defaultdict(list)
        for col_key, col_info in columns.items():
            dataset = col_info['dataset']
            columns_by_dataset[dataset].append(col_info)
        
        for dataset, cols in columns_by_dataset.items():
            escaped_dataset = self._escape_string(dataset)
            
            for col in cols:
                col_name = col['column_name']
                escaped_col = self._escape_string(col_name)
                col_id = self._generate_column_id(dataset, col_name)
                
                # Create column node
                props = [
                    f".property('column_id', '{col_id}')",
                    f".property('column_name', '{escaped_col}')",
                    f".property('dataset', '{escaped_dataset}')",
                    f".property('data_type', '{col.get('data_type', 'unknown')}')",
                    f".property('nullable', {str(col.get('nullable', True)).lower()})"
                ]
                
                if col.get('precision') is not None:
                    props.append(f".property('precision', {col['precision']})")
                if col.get('scale') is not None:
                    props.append(f".property('scale', {col['scale']})")
                
                props_str = ''.join(props)
                
                # Create column node
                query = f"""
                    g.V().has('column', 'column_id', '{col_id}')
                    .fold()
                    .coalesce(
                        unfold(),
                        addV('column'){props_str}
                    )
                """
                self._execute_query(query)
                
                # Establish dataset to column relationship
                edge_query = f"""
                    g.V().has('dataset', 'node_name', '{escaped_dataset}').as('d')
                    .V().has('column', 'column_id', '{col_id}')
                    .coalesce(
                        inE('has_column').where(outV().as('d')),
                        addE('has_column').from('d')
                    )
                """
                self._execute_query(edge_query)
                self.stats['columns_created'] += 1
    
    def _write_lineage_edges(self, lineage):
        """Write table-level lineage edges"""
        for source, targets in lineage.items():
            if not targets:
                continue
                
            escaped_source = self._escape_string(source)
            
            for target in targets:
                escaped_target = self._escape_string(target)
                
                query = f"""
                    g.V().has('dataset', 'node_name', '{escaped_source}').as('s')
                    .V().has('dataset', 'node_name', '{escaped_target}')
                    .coalesce(
                        inE('data_flow').where(outV().as('s')),
                        addE('data_flow').from('s')
                        .property('edge_type', 'table_lineage')
                    )
                """
                self._execute_query(query)
                self.stats['lineage_edges'] += 1
    
    def _write_column_lineage(self, column_lineage):
        """Write column-level lineage relationships"""
        for target_col, source_info in column_lineage.items():
            if not source_info:
                continue
            
            # Parse target column
            target_parts = target_col.split('.')
            if len(target_parts) < 2:
                continue
            
            target_dataset = '.'.join(target_parts[:-1])
            target_column = target_parts[-1]
            target_id = self._generate_column_id(target_dataset, target_column)
            
            # Process source columns
            if isinstance(source_info, list):
                for source in source_info:
                    self._create_column_lineage_edge(source, target_id)
            elif isinstance(source_info, dict):
                self._create_column_lineage_edge(source_info, target_id)
    
    def _create_column_lineage_edge(self, source_info, target_id):
        """Create column-level lineage edge"""
        if isinstance(source_info, dict):
            source_table = source_info.get('source_table', '')
            source_column = source_info.get('source_column', '')
            transformation = source_info.get('transformation', 'direct')
            
            if source_table and source_column:
                source_id = self._generate_column_id(source_table, source_column)
                
                query = f"""
                    g.V().has('column', 'column_id', '{source_id}').as('s')
                    .V().has('column', 'column_id', '{target_id}')
                    .coalesce(
                        inE('column_lineage').where(outV().as('s')),
                        addE('column_lineage').from('s')
                        .property('transformation', '{transformation}')
                    )
                """
                self._execute_query(query)
                self.stats['column_edges'] += 1
    
    def _generate_column_id(self, dataset, column):
        """Generate unique column ID using SHA-256 for security"""
        return hashlib.sha256(f"{dataset}.{column}".encode()).hexdigest()
    
    def _escape_string(self, s):
        """Escape special characters in strings"""
        if not s:
            return s
        return s.replace("'", "\\'").replace('"', '\\"')
    
    def _execute_query(self, query):
        """Execute Neptune query"""
        try:
            request = AWSRequest(
                method='POST',
                url=self.endpoint,
                data=json.dumps({'gremlin': query})
            )
            signed_headers = self._sign_request(request)
            response = self._send_request(
                self.endpoint,
                signed_headers,
                json.dumps({'gremlin': query})
            )
            return response
        except Exception as e:
            logger.warning(f"Query execution failed: {str(e)}")
            return None
    
    def _sign_request(self, request):
        """Sign AWS request"""
        credentials = get_credentials(Session())
        auth = SigV4Auth(credentials, 'neptune-db', self.aws_region)
        auth.add_auth(request)
        return dict(request.headers)
    
    def _send_request(self, url, headers, data):
        """Send request to Neptune"""
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request Error: {str(e)}")
            return None

def main():
    """Main function"""
    # Get configuration from environment variables or defaults
    raw_data_path = os.getenv('RAW_DATA_PATH', './raw-data')
    neptune_endpoint = os.getenv('NEPTUNE_ENDPOINT')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    if not neptune_endpoint:
        logger.error("NEPTUNE_ENDPOINT environment variable is required")
        sys.exit(1)
    
    # Initialize processor
    processor = EC2LineageProcessor(raw_data_path, neptune_endpoint, aws_region)
    
    # Process lineage
    success = processor.process_lineage()
    
    if success:
        logger.info("Lineage processing completed successfully")
        sys.exit(0)
    else:
        logger.error("Lineage processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main()