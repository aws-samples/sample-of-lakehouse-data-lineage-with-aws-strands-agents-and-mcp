#!/usr/bin/env python3
"""
Enhanced EC2 Data Lineage Processing Script with Source Tracking
Tracks whether nodes come from Athena, Redshift, or both
Security-enhanced version addressing Bandit scan findings
"""

import json
import os
import sys
import time
import secrets  # Use secrets instead of random for cryptographic randomness
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.session import Session
except ImportError as e:
    print(f"Error: Missing required module - {e}")
    print("\nPlease install: python3 -m pip install boto3")
    sys.exit(1)

import urllib.request
import urllib.error
import urllib.parse

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

# Reduce boto3 logging verbosity
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)


class DataLineageProcessor:
    """Data Lineage Processor with Source Tracking and Enhanced Security"""
    
    # Allowed URL schemes for security
    ALLOWED_SCHEMES = ('https',)
    
    def __init__(self, raw_data_path: str, neptune_endpoint: str, aws_region: str = 'us-east-1'):
        """
        Initialize the processor
        
        Args:
            raw_data_path: Path to the raw-data directory
            neptune_endpoint: Neptune endpoint URL
            aws_region: AWS region for Neptune
        """
        self.raw_data_path = Path(raw_data_path)
        self.aws_region = aws_region
        
        # Validate and format Neptune URL with security checks
        self.neptune_endpoint = self._validate_neptune_endpoint(neptune_endpoint)
        
        # Track processed items and their sources
        self.processed_nodes = set()
        self.processed_edges = set()
        self.node_sources = {}  # Track source of each node: {node: set(['athena', 'redshift'])}
        self.failed_operations = []
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'athena_nodes': 0,
            'redshift_nodes': 0,
            'shared_nodes': 0,
            'total_nodes': 0,
            'edges_created': 0,
            'retries': 0,
            'failures': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("="*60)
        logger.info("Data Lineage Processor with Source Tracking")
        logger.info("="*60)
        logger.info(f"  Data path: {self.raw_data_path}")
        logger.info(f"  Neptune endpoint: {self.neptune_endpoint}")
        logger.info(f"  AWS region: {self.aws_region}")
        logger.info("="*60)
    
    def _validate_neptune_endpoint(self, neptune_endpoint: str) -> str:
        """
        Validate and format Neptune endpoint URL
        
        Args:
            neptune_endpoint: Neptune endpoint URL
            
        Returns:
            Validated and formatted URL
            
        Raises:
            ValueError: If URL is invalid or uses disallowed scheme
        """
        if neptune_endpoint.startswith('https://'):
            url = neptune_endpoint
        else:
            url = f'https://{neptune_endpoint}:8182/gremlin'
        
        # Parse and validate URL
        parsed_url = urllib.parse.urlparse(url)
        
        # Security check: ensure only HTTPS is used
        if parsed_url.scheme not in self.ALLOWED_SCHEMES:
            raise ValueError(f"Invalid URL scheme: {parsed_url.scheme}. Only HTTPS is allowed.")
        
        # Validate hostname exists
        if not parsed_url.netloc:
            raise ValueError("Invalid Neptune endpoint: missing hostname")
        
        return url
    
    def dbt_nodename_format(self, node_name: str) -> str:
        """Format DBT node names by extracting the last part after dot"""
        return node_name.split(".")[-1]
    
    def process_manifest_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Process a manifest JSON file and extract lineage map"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if already processed
            if "lineage_map" in data:
                logger.info(f"✓ Using existing lineage_map from {file_path.name}")
                return data["lineage_map"]
            
            # Process raw data
            if "child_map" in data:
                lineage_map = data["child_map"]
                node_dict = {}
                
                # Format node names
                for item in lineage_map:
                    lineage_map[item] = [self.dbt_nodename_format(child) 
                                       for child in lineage_map[item]]
                    node_dict[item] = self.dbt_nodename_format(item)
                
                # Update keys with formatted names
                lineage_map = {node_dict[old]: value 
                             for old, value in lineage_map.items()}
                
                logger.info(f"✓ Processed {file_path.name}: {len(lineage_map)} nodes")
                return lineage_map
            
            logger.warning(f"⚠ No child_map found in {file_path.name}")
            return {}
            
        except Exception as e:
            logger.error(f"✗ Error processing {file_path}: {e}")
            raise
    
    def read_local_files(self) -> Tuple[Dict, Dict]:
        """Read and process local manifest files"""
        logger.info("\n► Reading manifest files...")
        
        athena_file = self.raw_data_path / 'athena_manifest.json'
        redshift_file = self.raw_data_path / 'redshift_manifest.json'
        
        # Check file existence
        if not athena_file.exists():
            raise FileNotFoundError(f"File not found: {athena_file}")
        if not redshift_file.exists():
            raise FileNotFoundError(f"File not found: {redshift_file}")
        
        # Process files
        athena_data = self.process_manifest_file(athena_file)
        redshift_data = self.process_manifest_file(redshift_file)
        
        logger.info(f"  Athena nodes: {len(athena_data)}")
        logger.info(f"  Redshift nodes: {len(redshift_data)}")
        
        return athena_data, redshift_data
    
    def merge_data_with_source_tracking(self, athena_data: Dict, redshift_data: Dict) -> Tuple[Dict, Dict[str, Set[str]]]:
        """
        Merge Athena and Redshift data with source tracking
        
        Args:
            athena_data: Athena lineage data {node: [children]}
            redshift_data: Redshift lineage data {node: [children]}
            
        Returns:
            Tuple of (merged_data, node_sources)
            - merged_data: Combined lineage map
            - node_sources: Source tracking for each node
        """
        merged_data = {}
        node_sources = {}  # {node: set(['athena', 'redshift'])}
        
        # Process Athena data
        for node, children in athena_data.items():
            # Initialize node
            if node not in merged_data:
                merged_data[node] = []
                node_sources[node] = set()
            
            # Add children (avoid duplicates)
            for child in children:
                if child not in merged_data[node]:
                    merged_data[node].append(child)
                
                # Track child source
                if child not in node_sources:
                    node_sources[child] = set()
                node_sources[child].add('athena')
            
            # Mark parent node as from Athena
            node_sources[node].add('athena')
        
        # Process Redshift data
        for node, children in redshift_data.items():
            # Initialize node
            if node not in merged_data:
                merged_data[node] = []
                node_sources[node] = set()
            
            # Add children (avoid duplicates)
            for child in children:
                if child not in merged_data[node]:
                    merged_data[node].append(child)
                
                # Track child source
                if child not in node_sources:
                    node_sources[child] = set()
                node_sources[child].add('redshift')
            
            # Mark parent node as from Redshift
            node_sources[node].add('redshift')
        
        # Ensure all nodes exist as keys
        all_nodes = set(merged_data.keys())
        for children_list in merged_data.values():
            all_nodes.update(children_list)
        
        for node in all_nodes:
            if node not in merged_data:
                merged_data[node] = []  # Leaf nodes have no children
            if node not in node_sources:
                node_sources[node] = set(['unknown'])
        
        # Calculate statistics
        athena_only = [node for node, sources in node_sources.items() if sources == {'athena'}]
        redshift_only = [node for node, sources in node_sources.items() if sources == {'redshift'}]
        shared_nodes = [node for node, sources in node_sources.items() if len(sources) > 1 and 'unknown' not in sources]
        
        self.stats['athena_nodes'] = len(athena_only)
        self.stats['redshift_nodes'] = len(redshift_only)
        self.stats['shared_nodes'] = len(shared_nodes)
        self.stats['total_nodes'] = len(merged_data)
        
        logger.info(f"\n► Merged data with source tracking:")
        logger.info(f"  Total nodes: {len(merged_data)}")
        logger.info(f"  Athena-only nodes: {len(athena_only)}")
        logger.info(f"  Redshift-only nodes: {len(redshift_only)}")
        logger.info(f"  Shared nodes (appear in both): {len(shared_nodes)}")
        
        if shared_nodes:
            logger.info(f"  Examples of shared nodes: {shared_nodes[:5]}")
        
        self.node_sources = node_sources
        return merged_data, node_sources
    
    def sign_request(self, request: AWSRequest) -> Dict:
        """Sign AWS request for Neptune authentication"""
        session = Session()
        credentials = session.get_credentials()
        auth = SigV4Auth(credentials, 'neptune-db', self.aws_region)
        auth.add_auth(request)
        return dict(request.headers)
    
    def _generate_jitter(self) -> float:
        """
        Generate cryptographically secure random jitter for retry delays
        
        Returns:
            Float between 0 and 0.5
        """
        # Use secrets module for secure random generation
        return secrets.SystemRandom().uniform(0, 0.5)
    
    def _safe_urlopen(self, req: urllib.request.Request, timeout: int = 30):
        """
        Safely open URL with validation
        
        Args:
            req: The request object
            timeout: Timeout in seconds
            
        Returns:
            Response object
            
        Raises:
            ValueError: If URL scheme is not allowed
        """
        # Additional safety check before opening URL
        url = req.full_url
        parsed_url = urllib.parse.urlparse(url)
        
        if parsed_url.scheme not in self.ALLOWED_SCHEMES:
            raise ValueError(f"Attempted to open URL with disallowed scheme: {parsed_url.scheme}")
        
        return urllib.request.urlopen(req, timeout=timeout)  # nosec B310 - URL scheme validated above
    
    def execute_gremlin_with_retry(self, query: str, max_retries: int = 3) -> Optional[str]:
        """Execute Gremlin query with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                # Prepare request
                request = AWSRequest(
                    method='POST',
                    url=self.neptune_endpoint,
                    data=json.dumps({'gremlin': query})
                )
                signed_headers = self.sign_request(request)
                
                # Execute request
                req = urllib.request.Request(
                    self.neptune_endpoint,
                    data=json.dumps({'gremlin': query}).encode('utf-8'),
                    headers=signed_headers,
                    method='POST'
                )
                
                with self._safe_urlopen(req, timeout=30) as response:
                    return response.read().decode('utf-8')
                    
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                
                # Handle concurrent modification exceptions
                if "ConcurrentModificationException" in error_body:
                    if attempt < max_retries - 1:
                        # Exponential backoff with secure jitter
                        wait_time = 0.5 * (2 ** attempt) + self._generate_jitter()
                        logger.debug(f"  Retry {attempt + 1}/{max_retries} in {wait_time:.2f}s...")
                        time.sleep(wait_time)
                        self.stats['retries'] += 1
                        continue
                    else:
                        logger.warning(f"  Max retries reached")
                        self.stats['failures'] += 1
                        return None
                else:
                    logger.error(f"  Query error: {e.code}")
                    return None
                    
            except Exception as e:
                logger.error(f"  Unexpected error: {e}")
                return None
        
        return None
    
    def clear_neptune_database(self):
        """Clear all data from Neptune database"""
        logger.info("\n► Clearing Neptune database...")
        
        result = self.execute_gremlin_with_retry("g.V().drop()")
        if result:
            logger.info("  ✓ Database cleared successfully")
        
        # Verify the database is empty
        count_result = self.execute_gremlin_with_retry("g.V().count()")
        if count_result:
            try:
                response = json.loads(count_result)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Vertex count: {count}")
            except Exception as e:
                logger.debug(f"  Count result parsing error: {e}")
                logger.debug(f"  Raw result: {count_result[:100]}")
    
    def create_node_with_source(self, node_name: str, source_type: str) -> bool:
        """
        Create a node with source type property
        
        Args:
            node_name: Name of the node
            source_type: Source type ('athena', 'redshift', or 'athena,redshift')
            
        Returns:
            True if successful, False otherwise
        """
        # Check if already processed
        with self.lock:
            if node_name in self.processed_nodes:
                return True
        
        # Escape single quotes
        escaped_node = node_name.replace("'", "\\'")
        
        # Create node with source_type property
        query = (
            f"g.V().has('lineage_node', 'node_name', '{escaped_node}')"
            f".fold().coalesce(unfold(), "
            f"addV('lineage_node')"
            f".property('node_name', '{escaped_node}')"
            f".property('source_type', '{source_type}')"
            f".property('created_timestamp', '{datetime.now().isoformat()}')"
            f")"
        )
        
        result = self.execute_gremlin_with_retry(query)
        
        if result:
            with self.lock:
                self.processed_nodes.add(node_name)
            return True
        return False
    
    def create_edge_with_metadata(self, parent: str, child: str, parent_source: str, child_source: str) -> bool:
        """
        Create an edge with metadata about the relationship
        
        Args:
            parent: Parent node name
            child: Child node name
            parent_source: Source type of parent
            child_source: Source type of child
            
        Returns:
            True if successful, False otherwise
        """
        edge_key = f"{parent}->{child}"
        
        # Check if already processed
        with self.lock:
            if edge_key in self.processed_edges:
                return True
        
        # Ensure both nodes exist with their source types
        if not self.create_node_with_source(parent, parent_source):
            return False
        if not self.create_node_with_source(child, child_source):
            return False
        
        # Escape single quotes
        escaped_parent = parent.replace("'", "\\'")
        escaped_child = child.replace("'", "\\'")
        
        # Determine edge type based on sources
        edge_type = 'cross_system' if parent_source != child_source else 'same_system'
        
        # Create edge with metadata
        query = (
            f"g.V().has('lineage_node', 'node_name', '{escaped_parent}').as('p')"
            f".V().has('lineage_node', 'node_name', '{escaped_child}')"
            f".coalesce("
            f"  inE('data_flow').where(outV().as('p')),"
            f"  addE('data_flow').from('p')"
            f"  .property('edge_type', '{edge_type}')"
            f"  .property('parent_source', '{parent_source}')"
            f"  .property('child_source', '{child_source}')"
            f"  .property('created_timestamp', '{datetime.now().isoformat()}')"
            f")"
        )
        
        result = self.execute_gremlin_with_retry(query, max_retries=5)
        
        if result:
            with self.lock:
                self.processed_edges.add(edge_key)
                self.stats['edges_created'] += 1
            return True
        else:
            # Record failure for later retry
            self.failed_operations.append(('edge', parent, child, parent_source, child_source))
            return False
    
    def process_node_batch_with_sources(self, batch: List[Tuple[str, List[str], Dict[str, Set[str]]]]):
        """
        Process a batch of nodes with source tracking
        
        Args:
            batch: List of (node, children, node_sources) tuples
        """
        for node, children, all_node_sources in batch:
            try:
                # Get source type for parent node
                parent_sources = all_node_sources.get(node, set(['unknown']))
                parent_source_type = ','.join(sorted(parent_sources))
                
                # Create parent node with source
                self.create_node_with_source(node, parent_source_type)
                
                # Create children and edges with source metadata
                for child in children:
                    child_sources = all_node_sources.get(child, set(['unknown']))
                    child_source_type = ','.join(sorted(child_sources))
                    
                    self.create_edge_with_metadata(node, child, parent_source_type, child_source_type)
                    
            except Exception as e:
                logger.error(f"Error processing {node}: {e}")
                self.failed_operations.append(('node', node, children))
    
    def write_to_neptune_with_sources(self, data: Dict, node_sources: Dict[str, Set[str]]):
        """
        Write lineage data to Neptune with source tracking
        
        Args:
            data: Dictionary of node relationships
            node_sources: Source tracking for each node
        """
        logger.info(f"\n► Writing {len(data)} nodes to Neptune with source metadata...")
        logger.info("  Processing in batches to minimize conflicts...")
        
        self.stats['start_time'] = time.time()
        
        # Clear existing data
        self.clear_neptune_database()
        
        # Process in batches
        batch_size = 5  # Small batch size for stability
        max_workers = 2  # Limited parallelism
        items = [(node, children, node_sources) for node, children in data.items()]
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        logger.info(f"  Total batches: {total_batches} (batch size: {batch_size})")
        
        for batch_num, i in enumerate(range(0, len(items), batch_size), 1):
            batch = items[i:i+batch_size]
            
            # Process batch with limited parallelism
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self.process_node_batch_with_sources, [item])
                    for item in batch
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"  Batch processing error: {e}")
            
            # Add delay between batches to avoid conflicts
            if i + batch_size < len(items):
                time.sleep(0.3)  # 300ms delay
            
            # Progress update
            processed = min(i + batch_size, len(items))
            logger.info(f"  Progress: {processed}/{len(items)} nodes "
                       f"(Batch {batch_num}/{total_batches})")
        
        # Retry failed operations
        self.retry_failed_operations_with_sources()
        
        self.stats['end_time'] = time.time()
        
        # Log statistics
        self.log_statistics()
    
    def retry_failed_operations_with_sources(self):
        """Retry any failed operations with source information"""
        if not self.failed_operations:
            return
        
        logger.info(f"\n► Retrying {len(self.failed_operations)} failed operations...")
        
        retry_count = 0
        for op_type, *args in self.failed_operations[:]:  # Copy list
            if op_type == 'edge' and len(args) == 4:
                parent, child, parent_source, child_source = args
                if self.create_edge_with_metadata(parent, child, parent_source, child_source):
                    self.failed_operations.remove((op_type, *args))
                    retry_count += 1
            elif op_type == 'node':
                # Process node with its children
                node, children = args[0], args[1]
                success = True
                parent_sources = self.node_sources.get(node, set(['unknown']))
                parent_source_type = ','.join(sorted(parent_sources))
                
                for child in children:
                    child_sources = self.node_sources.get(child, set(['unknown']))
                    child_source_type = ','.join(sorted(child_sources))
                    
                    if not self.create_edge_with_metadata(node, child, parent_source_type, child_source_type):
                        success = False
                
                if success:
                    self.failed_operations.remove((op_type, *args))
                    retry_count += 1
        
        logger.info(f"  ✓ Successfully retried: {retry_count}")
        
        if self.failed_operations:
            logger.warning(f"  ⚠ Still failed: {len(self.failed_operations)}")
            for op in self.failed_operations[:5]:  # Show first 5
                logger.warning(f"    - {op}")
    
    def verify_neptune_data_with_sources(self):
        """Verify the data written to Neptune including source information"""
        logger.info("\n► Verifying Neptune data with source information...")
        
        # Count total nodes
        node_result = self.execute_gremlin_with_retry("g.V().count()")
        if node_result:
            try:
                response = json.loads(node_result)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Total nodes in Neptune: {count}")
            except Exception as e:
                logger.debug(f"  Error parsing node count: {e}")
        
        # Count nodes by source type
        athena_count = self.execute_gremlin_with_retry("g.V().has('source_type', 'athena').count()")
        if athena_count:
            try:
                response = json.loads(athena_count)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Athena-only nodes: {count}")
            except Exception:
                logger.debug("  Could not parse Athena count")
        
        redshift_count = self.execute_gremlin_with_retry("g.V().has('source_type', 'redshift').count()")
        if redshift_count:
            try:
                response = json.loads(redshift_count)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Redshift-only nodes: {count}")
            except Exception:
                logger.debug("  Could not parse Redshift count")
        
        shared_count = self.execute_gremlin_with_retry("g.V().has('source_type', 'athena,redshift').count()")
        if shared_count:
            try:
                response = json.loads(shared_count)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Shared nodes (Athena+Redshift): {count}")
            except Exception:
                logger.debug("  Could not parse shared count")
        
        # Count edges
        edge_result = self.execute_gremlin_with_retry("g.E().count()")
        if edge_result:
            try:
                response = json.loads(edge_result)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Total edges in Neptune: {count}")
            except Exception as e:
                logger.debug(f"  Error parsing edge count: {e}")
        
        # Count cross-system edges
        cross_edge_result = self.execute_gremlin_with_retry("g.E().has('edge_type', 'cross_system').count()")
        if cross_edge_result:
            try:
                response = json.loads(cross_edge_result)
                count = response['result']['data'][0]['@value']
                logger.info(f"  Cross-system edges: {count}")
            except Exception:
                logger.debug("  Could not parse cross-system edge count")
        
        # Sample nodes with sources
        sample_result = self.execute_gremlin_with_retry(
            "g.V().limit(5).project('name', 'source').by('node_name').by('source_type')"
        )
        if sample_result:
            try:
                response = json.loads(sample_result)
                samples = response['result']['data']
                logger.info("  Sample nodes with sources:")
                for sample in samples:
                    name = sample['@value']['name']['@value']
                    source = sample['@value']['source']['@value']
                    logger.info(f"    - {name}: {source}")
            except Exception:
                logger.debug("  Could not parse sample nodes")
    
    def log_statistics(self):
        """Log processing statistics"""
        elapsed = self.stats['end_time'] - self.stats['start_time'] if self.stats['end_time'] else 0
        
        logger.info("\n" + "="*60)
        logger.info("Processing Statistics")
        logger.info("="*60)
        logger.info(f"  Total nodes: {self.stats['total_nodes']}")
        logger.info(f"  Athena-only nodes: {self.stats['athena_nodes']}")
        logger.info(f"  Redshift-only nodes: {self.stats['redshift_nodes']}")
        logger.info(f"  Shared nodes: {self.stats['shared_nodes']}")
        logger.info(f"  Edges created: {self.stats['edges_created']}")
        logger.info(f"  Retries: {self.stats['retries']}")
        logger.info(f"  Failures: {len(self.failed_operations)}")
        logger.info(f"  Time elapsed: {elapsed:.2f} seconds")
        if elapsed > 0:
            rate = self.stats['edges_created'] / elapsed
            logger.info(f"  Processing rate: {rate:.1f} edges/second")
        logger.info("="*60)
    
    def save_analysis_report(self, merged_data: Dict, node_sources: Dict[str, Set[str]]):
        """Save detailed analysis report with source information"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save merged data with sources
        output_file = self.raw_data_path / f'merged_lineage_with_sources_{timestamp}.json'
        output_data = {
            'lineage_map': merged_data,
            'node_sources': {node: list(sources) for node, sources in node_sources.items()},
            'statistics': {
                'total_nodes': self.stats['total_nodes'],
                'athena_nodes': self.stats['athena_nodes'],
                'redshift_nodes': self.stats['redshift_nodes'],
                'shared_nodes': self.stats['shared_nodes']
            },
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"\n► Saved analysis report to: {output_file}")
        
        # Create CSV report for easy analysis
        csv_file = self.raw_data_path / f'lineage_sources_{timestamp}.csv'
        with open(csv_file, 'w') as f:
            f.write("Node,Source,Children_Count\n")
            for node, children in merged_data.items():
                sources = ','.join(sorted(node_sources.get(node, set(['unknown']))))
                f.write(f"{node},{sources},{len(children)}\n")
        logger.info(f"► Saved CSV report to: {csv_file}")
    
    def process(self):
        """Main processing function"""
        try:
            logger.info("\n" + "="*60)
            logger.info("Starting Data Lineage Processing with Source Tracking")
            logger.info("="*60)
            
            # Read manifest files
            athena_data, redshift_data = self.read_local_files()
            
            # Merge data with source tracking
            merged_data, node_sources = self.merge_data_with_source_tracking(athena_data, redshift_data)
            
            # Save analysis report
            self.save_analysis_report(merged_data, node_sources)
            
            # Write to Neptune with source metadata
            self.write_to_neptune_with_sources(merged_data, node_sources)
            
            # Verify data
            self.verify_neptune_data_with_sources()
            
            logger.info("\n" + "="*60)
            logger.info("✓ Data Lineage Processing with Source Tracking Completed!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"\n✗ Processing failed: {e}")
            raise


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Data Lineage Processor with Source Tracking'
    )
    parser.add_argument(
        '--data-path',
        default=os.environ.get('RAW_DATA_PATH', '/home/ec2-user/raw-data'),
        help='Path to directory containing manifest files'
    )
    parser.add_argument(
        '--neptune',
        default=os.environ.get('NEPTUNE_ENDPOINT', ''),
        help='Neptune cluster endpoint'
    )
    parser.add_argument(
        '--region',
        default=os.environ.get('AWS_REGION', 'us-east-1'),
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    # Validate Neptune endpoint
    if not args.neptune:
        print("\n✗ Error: Neptune endpoint is required!")
        print("\nPlease provide it using one of these methods:")
        print("  1. Set environment variable: export NEPTUNE_ENDPOINT=your-cluster.neptune.amazonaws.com")
        print("  2. Use command line argument: --neptune your-cluster.neptune.amazonaws.com")
        sys.exit(1)
    
    # Convert to absolute path if needed
    data_path = args.data_path
    if not os.path.isabs(data_path):
        script_dir = Path(__file__).parent
        data_path = script_dir / data_path
    
    # Initialize and run processor
    try:
        processor = DataLineageProcessor(
            raw_data_path=str(data_path),
            neptune_endpoint=args.neptune,
            aws_region=args.region
        )
        processor.process()
    except KeyboardInterrupt:
        logger.info("\n\n⚠ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()