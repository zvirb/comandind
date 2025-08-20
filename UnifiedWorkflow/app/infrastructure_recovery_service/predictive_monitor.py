"""
Predictive Health Monitoring System
ML-based failure prediction and health scoring
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import redis.asyncio as redis
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

from config import infrastructure_recovery_config

logger = logging.getLogger(__name__)


class HealthMetric:
    """Individual health metric representation"""
    
    def __init__(self, name: str, value: float, timestamp: datetime, 
                 service: str, severity: str = "info"):
        self.name = name
        self.value = value
        self.timestamp = timestamp
        self.service = service
        self.severity = severity
        self.normalized_value = None


class PredictiveHealthMonitor:
    """
    Predictive Health Monitoring with ML-based failure prediction
    Implements industry-leading predictive analytics for infrastructure health
    """
    
    def __init__(self):
        self.config = infrastructure_recovery_config
        self.redis_client = None
        self.session = None
        self.health_scores: Dict[str, float] = {}
        self.prediction_models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_history: Dict[str, List[Dict]] = {}
        self.last_model_update = {}
        self.running = False
        
        # Initialize ML models for each service
        self.init_prediction_models()
    
    def init_prediction_models(self):
        """Initialize ML models for predictive monitoring"""
        for service in self.config.MONITORED_SERVICES:
            # Isolation Forest for anomaly detection
            self.prediction_models[f"{service}_anomaly"] = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            
            # Random Forest for failure prediction
            self.prediction_models[f"{service}_failure"] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # Standard scaler for feature normalization
            self.scalers[service] = StandardScaler()
            
            # Initialize feature history
            self.feature_history[service] = []
            
            # Initialize last update time
            self.last_model_update[service] = time.time()
    
    async def initialize(self):
        """Initialize monitoring connections and systems"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                self.config.REDIS_URL,
                decode_responses=True,
                health_check_interval=30
            )
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            logger.info("Predictive Health Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Predictive Health Monitor: {e}")
            raise
    
    async def start_monitoring(self):
        """Start the predictive monitoring system"""
        self.running = True
        
        tasks = [
            self.collect_metrics_loop(),
            self.health_analysis_loop(),
            self.model_update_loop(),
            self.prediction_loop()
        ]
        
        logger.info("Starting predictive monitoring system")
        await asyncio.gather(*tasks)
    
    async def collect_metrics_loop(self):
        """Main loop for collecting infrastructure metrics"""
        while self.running:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(self.config.FEATURE_COLLECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)
    
    async def collect_all_metrics(self):
        """Collect metrics from all monitored services"""
        tasks = []
        
        for service in self.config.MONITORED_SERVICES:
            tasks.append(self.collect_service_metrics(service))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for service, result in zip(self.config.MONITORED_SERVICES, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to collect metrics for {service}: {result}")
    
    async def collect_service_metrics(self, service: str) -> Dict[str, Any]:
        """Collect comprehensive metrics for a specific service"""
        metrics = {
            "service": service,
            "timestamp": datetime.utcnow(),
            "features": {}
        }
        
        try:
            # Collect Prometheus metrics
            prometheus_metrics = await self.query_prometheus_metrics(service)
            metrics["features"].update(prometheus_metrics)
            
            # Collect health check metrics
            health_metrics = await self.collect_health_check_metrics(service)
            metrics["features"].update(health_metrics)
            
            # Collect resource utilization metrics
            resource_metrics = await self.collect_resource_metrics(service)
            metrics["features"].update(resource_metrics)
            
            # Collect dependency health metrics
            dependency_metrics = await self.collect_dependency_metrics(service)
            metrics["features"].update(dependency_metrics)
            
            # Store metrics in feature history
            self.feature_history[service].append(metrics)
            
            # Maintain history size (keep last 1000 entries)
            if len(self.feature_history[service]) > 1000:
                self.feature_history[service] = self.feature_history[service][-1000:]
            
            # Cache metrics in Redis
            await self.cache_metrics(service, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for {service}: {e}")
            return metrics
    
    async def query_prometheus_metrics(self, service: str) -> Dict[str, float]:
        """Query Prometheus for service-specific metrics"""
        metrics = {}
        
        try:
            # Define metric queries for different services
            metric_queries = {
                "cpu_usage": f'rate(container_cpu_usage_seconds_total{{name=~".*{service}.*"}}[5m]) * 100',
                "memory_usage": f'container_memory_usage_bytes{{name=~".*{service}.*"}}',
                "memory_limit": f'container_spec_memory_limit_bytes{{name=~".*{service}.*"}}',
                "network_rx": f'rate(container_network_receive_bytes_total{{name=~".*{service}.*"}}[5m])',
                "network_tx": f'rate(container_network_transmit_bytes_total{{name=~".*{service}.*"}}[5m])',
                "restart_count": f'increase(container_start_time_seconds{{name=~".*{service}.*"}}[10m])'
            }
            
            # Service-specific queries
            if service == "postgres":
                metric_queries.update({
                    "connections": "pg_stat_database_numbackends",
                    "slow_queries": "rate(pg_stat_statements_mean_time_ms[5m])",
                    "database_size": "pg_database_size_bytes"
                })
            elif service == "redis":
                metric_queries.update({
                    "redis_memory": "redis_memory_used_bytes",
                    "redis_connections": "redis_connected_clients",
                    "cache_hit_rate": "rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))"
                })
            elif service == "qdrant":
                metric_queries.update({
                    "vectors_count": "qdrant_collections_vectors_count",
                    "search_requests": "rate(qdrant_search_requests_total[5m])"
                })
            
            # Execute queries
            for metric_name, query in metric_queries.items():
                try:
                    value = await self.execute_prometheus_query(query)
                    metrics[metric_name] = value
                except Exception as e:
                    logger.debug(f"Failed to query {metric_name} for {service}: {e}")
                    metrics[metric_name] = 0.0
            
        except Exception as e:
            logger.error(f"Error querying Prometheus for {service}: {e}")
        
        return metrics
    
    async def execute_prometheus_query(self, query: str) -> float:
        """Execute a single Prometheus query"""
        try:
            url = f"{self.config.PROMETHEUS_URL}/api/v1/query"
            params = {"query": query}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == "success" and data["data"]["result"]:
                        return float(data["data"]["result"][0]["value"][1])
                
                return 0.0
                
        except Exception as e:
            logger.debug(f"Prometheus query failed: {e}")
            return 0.0
    
    async def collect_health_check_metrics(self, service: str) -> Dict[str, float]:
        """Collect health check metrics for service"""
        metrics = {}
        
        try:
            endpoint = self.config.SERVICE_HEALTH_ENDPOINTS.get(service)
            if not endpoint:
                return metrics
            
            start_time = time.time()
            
            if endpoint.startswith("http"):
                async with self.session.get(endpoint) as response:
                    response_time = time.time() - start_time
                    metrics["health_check_response_time"] = response_time
                    metrics["health_check_status"] = 1.0 if response.status == 200 else 0.0
                    metrics["health_check_status_code"] = float(response.status)
            else:
                # Handle non-HTTP health checks (postgres, redis)
                health_status = await self.execute_service_health_check(service, endpoint)
                metrics["health_check_status"] = 1.0 if health_status else 0.0
                metrics["health_check_response_time"] = time.time() - start_time
        
        except Exception as e:
            logger.debug(f"Health check failed for {service}: {e}")
            metrics["health_check_status"] = 0.0
            metrics["health_check_response_time"] = 30.0  # Timeout value
        
        return metrics
    
    async def execute_service_health_check(self, service: str, check_command: str) -> bool:
        """Execute service-specific health checks"""
        try:
            if service == "postgres":
                # Implement postgres health check
                return await self.check_postgres_health()
            elif service == "redis":
                # Implement redis health check
                return await self.check_redis_health()
            else:
                return True
                
        except Exception:
            return False
    
    async def check_postgres_health(self) -> bool:
        """Check PostgreSQL health"""
        try:
            # Simple connection test
            conn = psycopg2.connect(
                self.config.DATABASE_URL,
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception:
            return False
    
    async def check_redis_health(self) -> bool:
        """Check Redis health"""
        try:
            result = await self.redis_client.ping()
            return result is True
        except Exception:
            return False
    
    async def collect_resource_metrics(self, service: str) -> Dict[str, float]:
        """Collect resource utilization metrics"""
        metrics = {}
        
        try:
            # Calculate derived metrics
            if "memory_usage" in metrics and "memory_limit" in metrics:
                if metrics.get("memory_limit", 0) > 0:
                    metrics["memory_utilization"] = (
                        metrics["memory_usage"] / metrics["memory_limit"]
                    ) * 100
                else:
                    metrics["memory_utilization"] = 0.0
            
            # Add network total
            metrics["network_total"] = (
                metrics.get("network_rx", 0) + metrics.get("network_tx", 0)
            )
            
        except Exception as e:
            logger.debug(f"Error calculating resource metrics for {service}: {e}")
        
        return metrics
    
    async def collect_dependency_metrics(self, service: str) -> Dict[str, float]:
        """Collect dependency health metrics"""
        metrics = {}
        
        try:
            dependencies = self.config.CRITICAL_SERVICE_DEPENDENCIES.get(service, [])
            
            healthy_deps = 0
            total_deps = len(dependencies)
            
            for dep in dependencies:
                dep_health = self.health_scores.get(dep, 1.0)
                if dep_health > 0.7:
                    healthy_deps += 1
            
            if total_deps > 0:
                metrics["dependency_health_ratio"] = healthy_deps / total_deps
            else:
                metrics["dependency_health_ratio"] = 1.0
                
        except Exception as e:
            logger.debug(f"Error calculating dependency metrics for {service}: {e}")
        
        return metrics
    
    async def cache_metrics(self, service: str, metrics: Dict):
        """Cache metrics in Redis for quick access"""
        try:
            cache_key = f"infrastructure:metrics:{service}"
            cache_data = {
                "timestamp": metrics["timestamp"].isoformat(),
                "features": metrics["features"]
            }
            
            await self.redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                str(cache_data)
            )
            
        except Exception as e:
            logger.debug(f"Error caching metrics for {service}: {e}")
    
    async def health_analysis_loop(self):
        """Main loop for health score analysis"""
        while self.running:
            try:
                await self.calculate_health_scores()
                await asyncio.sleep(60)  # Update health scores every minute
                
            except Exception as e:
                logger.error(f"Error in health analysis loop: {e}")
                await asyncio.sleep(5)
    
    async def calculate_health_scores(self):
        """Calculate comprehensive health scores for all services"""
        for service in self.config.MONITORED_SERVICES:
            try:
                health_score = await self.calculate_service_health_score(service)
                self.health_scores[service] = health_score
                
                # Cache health score
                await self.redis_client.setex(
                    f"infrastructure:health_score:{service}",
                    300,
                    str(health_score)
                )
                
                # Log critical health scores
                if health_score < self.config.HEALTH_SCORE_THRESHOLD:
                    logger.warning(
                        f"Service {service} health score below threshold: {health_score:.2f}"
                    )
                
            except Exception as e:
                logger.error(f"Error calculating health score for {service}: {e}")
    
    async def calculate_service_health_score(self, service: str) -> float:
        """Calculate health score for a specific service using ML algorithms"""
        try:
            history = self.feature_history.get(service, [])
            if len(history) < 10:  # Need minimum data points
                return 1.0  # Default to healthy for new services
            
            # Extract features from recent history
            recent_features = [entry["features"] for entry in history[-10:]]
            
            if not recent_features:
                return 1.0
            
            # Convert to numpy array for ML processing
            feature_matrix = self.extract_feature_matrix(recent_features)
            
            if feature_matrix is None or len(feature_matrix) == 0:
                return 1.0
            
            # Get anomaly score using Isolation Forest
            anomaly_model = self.prediction_models.get(f"{service}_anomaly")
            if anomaly_model and hasattr(anomaly_model, "decision_function"):
                try:
                    # Normalize features
                    scaler = self.scalers.get(service)
                    if scaler and hasattr(scaler, "transform"):
                        normalized_features = scaler.transform(feature_matrix)
                    else:
                        normalized_features = feature_matrix
                    
                    # Calculate anomaly scores
                    anomaly_scores = anomaly_model.decision_function(normalized_features)
                    avg_anomaly_score = np.mean(anomaly_scores)
                    
                    # Convert to health score (higher anomaly score = healthier)
                    # Normalize anomaly score to 0-1 range
                    health_from_anomaly = max(0.0, min(1.0, (avg_anomaly_score + 0.5) / 1.0))
                    
                except Exception as e:
                    logger.debug(f"Anomaly detection failed for {service}: {e}")
                    health_from_anomaly = 1.0
            else:
                health_from_anomaly = 1.0
            
            # Calculate rule-based health score
            rule_based_health = self.calculate_rule_based_health(recent_features[-1])
            
            # Combine scores (weighted average)
            final_health_score = (
                0.6 * rule_based_health +
                0.4 * health_from_anomaly
            )
            
            return max(0.0, min(1.0, final_health_score))
            
        except Exception as e:
            logger.error(f"Error calculating health score for {service}: {e}")
            return 1.0  # Default to healthy on error
    
    def extract_feature_matrix(self, features_list: List[Dict]) -> Optional[np.ndarray]:
        """Extract numerical feature matrix from features list"""
        try:
            # Define expected features
            expected_features = [
                "cpu_usage", "memory_usage", "memory_utilization",
                "network_rx", "network_tx", "network_total",
                "health_check_status", "health_check_response_time",
                "dependency_health_ratio", "restart_count"
            ]
            
            feature_matrix = []
            
            for features in features_list:
                row = []
                for feature_name in expected_features:
                    value = features.get(feature_name, 0.0)
                    # Handle non-numeric values
                    if not isinstance(value, (int, float)):
                        value = 0.0
                    row.append(float(value))
                
                feature_matrix.append(row)
            
            return np.array(feature_matrix) if feature_matrix else None
            
        except Exception as e:
            logger.debug(f"Error extracting feature matrix: {e}")
            return None
    
    def calculate_rule_based_health(self, features: Dict[str, Any]) -> float:
        """Calculate rule-based health score"""
        try:
            health_score = 1.0
            
            # Health check status (critical)
            if features.get("health_check_status", 1.0) == 0.0:
                health_score *= 0.1  # Severe penalty for failed health checks
            
            # Response time penalty
            response_time = features.get("health_check_response_time", 0.0)
            if response_time > 10.0:
                health_score *= 0.8
            elif response_time > 5.0:
                health_score *= 0.9
            
            # CPU usage penalty
            cpu_usage = features.get("cpu_usage", 0.0)
            if cpu_usage > 90.0:
                health_score *= 0.7
            elif cpu_usage > 80.0:
                health_score *= 0.85
            
            # Memory utilization penalty
            memory_util = features.get("memory_utilization", 0.0)
            if memory_util > 95.0:
                health_score *= 0.6
            elif memory_util > 85.0:
                health_score *= 0.8
            
            # Dependency health penalty
            dep_health = features.get("dependency_health_ratio", 1.0)
            if dep_health < 0.5:
                health_score *= 0.7
            elif dep_health < 0.8:
                health_score *= 0.9
            
            # Restart count penalty
            restart_count = features.get("restart_count", 0.0)
            if restart_count > 2:
                health_score *= 0.5
            elif restart_count > 0:
                health_score *= 0.8
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            logger.debug(f"Error in rule-based health calculation: {e}")
            return 1.0
    
    async def model_update_loop(self):
        """Loop for updating ML models with new data"""
        while self.running:
            try:
                await self.update_prediction_models()
                await asyncio.sleep(self.config.ML_MODEL_UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in model update loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def update_prediction_models(self):
        """Update ML models with accumulated data"""
        for service in self.config.MONITORED_SERVICES:
            try:
                history = self.feature_history.get(service, [])
                
                # Need minimum samples for model training
                if len(history) < 100:
                    continue
                
                # Prepare training data
                X, y = self.prepare_training_data(service, history)
                
                if X is None or len(X) < 50:
                    continue
                
                # Update anomaly detection model
                anomaly_model = self.prediction_models.get(f"{service}_anomaly")
                if anomaly_model:
                    # Fit scaler
                    scaler = self.scalers[service]
                    X_scaled = scaler.fit_transform(X)
                    
                    # Train anomaly detector
                    anomaly_model.fit(X_scaled)
                    
                    logger.info(f"Updated anomaly detection model for {service}")
                
                # Update failure prediction model if we have labels
                if y is not None and len(y) > 10:
                    failure_model = self.prediction_models.get(f"{service}_failure")
                    if failure_model:
                        X_train, X_test, y_train, y_test = train_test_split(
                            X_scaled, y, test_size=0.2, random_state=42
                        )
                        
                        failure_model.fit(X_train, y_train)
                        
                        logger.info(f"Updated failure prediction model for {service}")
                
                # Update last update time
                self.last_model_update[service] = time.time()
                
            except Exception as e:
                logger.error(f"Error updating models for {service}: {e}")
    
    def prepare_training_data(self, service: str, history: List[Dict]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Prepare training data from historical metrics"""
        try:
            features_list = [entry["features"] for entry in history]
            X = self.extract_feature_matrix(features_list)
            
            if X is None:
                return None, None
            
            # Create labels based on health score thresholds
            # This is a simple labeling strategy - in production, you might use
            # actual incident data or more sophisticated labeling
            y = []
            for entry in history:
                features = entry["features"]
                
                # Label as failure (1) if multiple indicators suggest problems
                failure_indicators = 0
                
                if features.get("health_check_status", 1.0) == 0.0:
                    failure_indicators += 3  # Health check failure is critical
                
                if features.get("cpu_usage", 0.0) > 90.0:
                    failure_indicators += 1
                
                if features.get("memory_utilization", 0.0) > 95.0:
                    failure_indicators += 1
                
                if features.get("health_check_response_time", 0.0) > 10.0:
                    failure_indicators += 1
                
                if features.get("dependency_health_ratio", 1.0) < 0.5:
                    failure_indicators += 1
                
                if features.get("restart_count", 0.0) > 0:
                    failure_indicators += 1
                
                # Label as failure if 2 or more indicators
                y.append(1 if failure_indicators >= 2 else 0)
            
            return X, np.array(y) if y else None
            
        except Exception as e:
            logger.debug(f"Error preparing training data for {service}: {e}")
            return None, None
    
    async def prediction_loop(self):
        """Loop for generating failure predictions"""
        while self.running:
            try:
                await self.generate_predictions()
                await asyncio.sleep(300)  # Generate predictions every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                await asyncio.sleep(60)
    
    async def generate_predictions(self):
        """Generate failure predictions for all services"""
        predictions = {}
        
        for service in self.config.MONITORED_SERVICES:
            try:
                prediction = await self.predict_service_failure(service)
                predictions[service] = prediction
                
                # Cache prediction
                await self.redis_client.setex(
                    f"infrastructure:prediction:{service}",
                    600,  # 10 minutes TTL
                    str(prediction)
                )
                
                # Alert on high failure probability
                if prediction.get("failure_probability", 0.0) > 0.7:
                    logger.warning(
                        f"High failure probability for {service}: {prediction['failure_probability']:.2f}"
                    )
                
            except Exception as e:
                logger.error(f"Error generating prediction for {service}: {e}")
        
        # Store aggregated predictions
        await self.redis_client.setex(
            "infrastructure:predictions:all",
            600,
            str(predictions)
        )
    
    async def predict_service_failure(self, service: str) -> Dict[str, Any]:
        """Predict failure probability for a specific service"""
        try:
            history = self.feature_history.get(service, [])
            
            if len(history) < 10:
                return {
                    "failure_probability": 0.0,
                    "confidence": 0.0,
                    "predicted_time_to_failure": None,
                    "risk_factors": []
                }
            
            # Get recent features
            recent_features = [entry["features"] for entry in history[-10:]]
            X = self.extract_feature_matrix(recent_features)
            
            if X is None or len(X) == 0:
                return {"failure_probability": 0.0, "confidence": 0.0}
            
            # Get current health score
            current_health = self.health_scores.get(service, 1.0)
            
            # Calculate failure probability using multiple methods
            failure_prob = 0.0
            confidence = 0.0
            
            # Method 1: Current health score
            health_based_prob = 1.0 - current_health
            failure_prob += health_based_prob * 0.4
            
            # Method 2: Trend analysis
            if len(history) >= 20:
                recent_scores = []
                for entry in history[-20:]:
                    score = self.calculate_rule_based_health(entry["features"])
                    recent_scores.append(score)
                
                # Calculate trend
                trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                trend_based_prob = max(0.0, -trend)  # Negative trend = increasing failure risk
                failure_prob += trend_based_prob * 0.3
            
            # Method 3: ML model prediction (if trained)
            failure_model = self.prediction_models.get(f"{service}_failure")
            if failure_model and hasattr(failure_model, "predict_proba"):
                try:
                    scaler = self.scalers.get(service)
                    if scaler and hasattr(scaler, "transform"):
                        X_scaled = scaler.transform(X[-1:])  # Most recent sample
                        ml_probs = failure_model.predict_proba(X_scaled)[0]
                        ml_failure_prob = ml_probs[1] if len(ml_probs) > 1 else 0.0
                        failure_prob += ml_failure_prob * 0.3
                        confidence = 0.8  # Higher confidence with ML
                except Exception as e:
                    logger.debug(f"ML prediction failed for {service}: {e}")
            
            # Normalize probability
            failure_prob = max(0.0, min(1.0, failure_prob))
            
            # Identify risk factors
            risk_factors = self.identify_risk_factors(recent_features[-1])
            
            # Estimate time to failure (very rough estimate)
            time_to_failure = None
            if failure_prob > 0.5:
                # Rough estimate based on trend and current health
                hours_estimate = max(1, int((current_health / max(0.01, failure_prob)) * 24))
                time_to_failure = datetime.utcnow() + timedelta(hours=hours_estimate)
            
            return {
                "failure_probability": failure_prob,
                "confidence": confidence,
                "predicted_time_to_failure": time_to_failure.isoformat() if time_to_failure else None,
                "risk_factors": risk_factors,
                "current_health_score": current_health
            }
            
        except Exception as e:
            logger.error(f"Error predicting failure for {service}: {e}")
            return {"failure_probability": 0.0, "confidence": 0.0}
    
    def identify_risk_factors(self, features: Dict[str, Any]) -> List[str]:
        """Identify specific risk factors from current metrics"""
        risk_factors = []
        
        try:
            if features.get("health_check_status", 1.0) == 0.0:
                risk_factors.append("Health check failing")
            
            if features.get("cpu_usage", 0.0) > 80.0:
                risk_factors.append(f"High CPU usage: {features['cpu_usage']:.1f}%")
            
            if features.get("memory_utilization", 0.0) > 85.0:
                risk_factors.append(f"High memory usage: {features['memory_utilization']:.1f}%")
            
            if features.get("health_check_response_time", 0.0) > 5.0:
                risk_factors.append(f"Slow response time: {features['health_check_response_time']:.1f}s")
            
            if features.get("dependency_health_ratio", 1.0) < 0.8:
                risk_factors.append(f"Unhealthy dependencies: {features['dependency_health_ratio']:.1f}")
            
            if features.get("restart_count", 0.0) > 0:
                risk_factors.append(f"Recent restarts: {features['restart_count']}")
            
        except Exception as e:
            logger.debug(f"Error identifying risk factors: {e}")
        
        return risk_factors
    
    async def get_service_health_score(self, service: str) -> float:
        """Get current health score for a service"""
        return self.health_scores.get(service, 1.0)
    
    async def get_all_health_scores(self) -> Dict[str, float]:
        """Get health scores for all services"""
        return self.health_scores.copy()
    
    async def get_service_prediction(self, service: str) -> Dict[str, Any]:
        """Get failure prediction for a service"""
        try:
            cached_prediction = await self.redis_client.get(f"infrastructure:prediction:{service}")
            if cached_prediction:
                return eval(cached_prediction)  # Note: In production, use proper JSON deserialization
            
            # Generate fresh prediction if not cached
            return await self.predict_service_failure(service)
            
        except Exception as e:
            logger.error(f"Error getting prediction for {service}: {e}")
            return {"failure_probability": 0.0, "confidence": 0.0}
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False
        
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Predictive Health Monitor stopped")


# Global monitor instance
predictive_monitor = PredictiveHealthMonitor()