"""
Kubernetes Operations Plugin for ChatOps CLI

Provides Kubernetes cluster management commands through natural language.
Supports pod lifecycle, deployment management, service operations, and cluster inspection with safety validations.
"""

import re
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..base import (
    BasePlugin,
    CommandPlugin,
    PluginMetadata,
    PluginCapability,
    PluginPriority,
    plugin,
)
from ...core.langchain_integration import DevOpsCommand, CommandType, RiskLevel
from ...core.os_detection import os_detection


@plugin(
    name="kubernetes",
    version="1.0.0",
    description="Kubernetes cluster and workload management operations",
    author="ChatOps CLI Team",
    category="orchestration",
    tags=["kubernetes", "k8s", "pods", "deployments", "services", "devops"],
    priority=PluginPriority.HIGH,
)
class KubernetesPlugin(CommandPlugin):
    """
    Plugin for Kubernetes operations and cluster management.

    Provides commands for:
    - Pod lifecycle (get, describe, logs, exec, delete)
    - Deployment management (get, scale, rollout, delete)
    - Service operations (get, describe, expose)
    - Namespace management (get, create, delete)
    - Resource inspection (get all, describe, events)
    """

    def __init__(self):
        super().__init__()
        self._capabilities.extend([
            PluginCapability.CONTAINER_MANAGEMENT,
            PluginCapability.COMMAND_VALIDATION,
            PluginCapability.SYSTEM_MONITORING,
            PluginCapability.CLOUD_OPERATIONS
        ])

        # Kubernetes command patterns this plugin can handle
        self._command_patterns = [
            r".*kubectl\s+.*",
            r".*kubernetes\s+.*",
            r".*k8s\s+.*",
            r".*pod[s]?\s+.*",
            r".*deployment[s]?\s+.*",
            r".*service[s]?\s+.*",
            r".*namespace[s]?\s+.*",
            r".*cluster\s+.*",
            r".*get\s+pods.*",
            r".*describe\s+.*",
            r".*logs\s+.*",
            r".*scale\s+.*",
            r".*rollout\s+.*",
        ]

        # Safe kubectl commands whitelist
        self._safe_commands = {
            'get', 'describe', 'logs', 'version', 'cluster-info', 'config', 
            'explain', 'api-resources', 'api-versions', 'top'
        }

        # Commands requiring extra caution
        self._dangerous_commands = {
            'delete', 'kill', 'drain', 'cordon', 'uncordon', 'taint', 
            'patch', 'replace', 'edit', 'apply', 'create'
        }

    async def initialize(self) -> bool:
        """Initialize the Kubernetes plugin"""
        try:
            # Check if kubectl is available
            if not shutil.which("kubectl"):
                self.logger.warning("kubectl command not found in PATH")
                return False

            self.logger.info("Kubernetes plugin initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Kubernetes plugin: {e}")
            return False

    async def cleanup(self) -> bool:
        """Cleanup Kubernetes plugin resources"""
        self.logger.info("Kubernetes plugin cleanup complete")
        return True

    def can_handle(self, user_input: str, context: Dict[str, Any] = None) -> bool:
        """Check if this plugin can handle the user input"""
        user_input_lower = user_input.lower()

        # Check against command patterns
        for pattern in self._command_patterns:
            if re.search(pattern, user_input_lower):
                return True

        # Check for Kubernetes-related keywords
        k8s_keywords = [
            "kubectl", "kubernetes", "k8s", "pod", "pods", "deployment", 
            "deployments", "service", "services", "namespace", "namespaces",
            "cluster", "node", "nodes", "configmap", "secret", "ingress"
        ]

        return any(keyword in user_input_lower for keyword in k8s_keywords)

    async def generate_command(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> Optional[DevOpsCommand]:
        """Generate Kubernetes command from natural language input"""
        user_input_lower = user_input.lower()

        # Pod Operations
        if any(keyword in user_input_lower for keyword in ["get pods", "list pods", "show pods"]):
            return DevOpsCommand(
                command="kubectl get pods -o wide --all-namespaces",
                description="List all pods across all namespaces with detailed information",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get pods", "kubectl get pods -n <namespace>"]
            )

        elif any(keyword in user_input_lower for keyword in ["pod logs", "logs", "kubectl logs"]):
            return self._generate_pod_logs_command(user_input_lower)

        elif any(keyword in user_input_lower for keyword in ["describe pod", "pod details"]):
            return DevOpsCommand(
                command="kubectl describe pod <pod_name> -n <namespace>",
                description="Get detailed information about a specific pod (replace placeholders)",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get pod <pod> -o yaml"]
            )

        elif any(keyword in user_input_lower for keyword in ["delete pod", "remove pod"]):
            return DevOpsCommand(
                command="kubectl delete pod <pod_name> -n <namespace>",
                description="Delete a specific pod (replace with actual pod name and namespace)",
                command_type=CommandType.CONTAINER_MANAGEMENT,
                risk_level=RiskLevel.HIGH,
                requires_sudo=False,
                estimated_duration="< 10 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl delete pod <pod> --force --grace-period=0"]
            )

        # Deployment Operations
        elif any(keyword in user_input_lower for keyword in ["get deployments", "list deployments", "show deployments"]):
            return DevOpsCommand(
                command="kubectl get deployments -o wide --all-namespaces",
                description="List all deployments across all namespaces",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get deploy", "kubectl get deployments -n <namespace>"]
            )

        elif any(keyword in user_input_lower for keyword in ["scale deployment", "scale up", "scale down"]):
            return self._generate_scale_command(user_input_lower)

        elif any(keyword in user_input_lower for keyword in ["rollout", "deployment rollout"]):
            return self._generate_rollout_command(user_input_lower)

        # Service Operations
        elif any(keyword in user_input_lower for keyword in ["get services", "list services", "show services"]):
            return DevOpsCommand(
                command="kubectl get services -o wide --all-namespaces",
                description="List all services across all namespaces",
                command_type=CommandType.NETWORK,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get svc", "kubectl get services -n <namespace>"]
            )

        # Namespace Operations
        elif any(keyword in user_input_lower for keyword in ["get namespaces", "list namespaces", "show namespaces"]):
            return DevOpsCommand(
                command="kubectl get namespaces",
                description="List all namespaces in the cluster",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get ns"]
            )

        # Node Operations
        elif any(keyword in user_input_lower for keyword in ["get nodes", "list nodes", "show nodes"]):
            return DevOpsCommand(
                command="kubectl get nodes -o wide",
                description="List all nodes in the cluster with detailed information",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get nodes", "kubectl describe nodes"]
            )

        # Cluster Information
        elif any(keyword in user_input_lower for keyword in ["cluster info", "cluster-info", "cluster status"]):
            return DevOpsCommand(
                command="kubectl cluster-info && kubectl version --short",
                description="Show cluster information and kubectl version",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl cluster-info dump"]
            )

        # Resource Overview
        elif any(keyword in user_input_lower for keyword in ["get all", "show all", "cluster overview"]):
            return DevOpsCommand(
                command="kubectl get all --all-namespaces",
                description="Get overview of all resources across all namespaces",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 5 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get all -A"]
            )

        # Events
        elif any(keyword in user_input_lower for keyword in ["events", "show events"]):
            return DevOpsCommand(
                command="kubectl get events --sort-by='.lastTimestamp' --all-namespaces",
                description="Show recent cluster events sorted by timestamp",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl get events -A", "kubectl get events -n <namespace>"]
            )

        return None

    def _generate_pod_logs_command(self, user_input: str) -> DevOpsCommand:
        """Generate pod logs command"""
        if "tail" in user_input or "recent" in user_input:
            return DevOpsCommand(
                command="kubectl logs <pod_name> -n <namespace> --tail=50",
                description="Show recent logs from a specific pod (replace placeholders)",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl logs <pod> -f", "kubectl logs <pod> --since=1h"]
            )
        else:
            return DevOpsCommand(
                command="kubectl logs <pod_name> -n <namespace>",
                description="Show logs from a specific pod (replace with actual pod name and namespace)",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 5 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl logs <pod> --previous", "kubectl logs <pod> -c <container>"]
            )

    def _generate_scale_command(self, user_input: str) -> DevOpsCommand:
        """Generate deployment scaling command"""
        return DevOpsCommand(
            command="kubectl scale deployment <deployment_name> --replicas=<number> -n <namespace>",
            description="Scale a deployment to specified number of replicas (replace placeholders)",
            command_type=CommandType.CONTAINER_MANAGEMENT,
            risk_level=RiskLevel.MEDIUM,
            requires_sudo=False,
            estimated_duration="< 10 seconds",
            prerequisites=["kubectl"],
            alternative_commands=["kubectl patch deployment <deploy> -p '{\"spec\":{\"replicas\":<num>}}'"]
        )

    def _generate_rollout_command(self, user_input: str) -> DevOpsCommand:
        """Generate deployment rollout command"""
        if "status" in user_input:
            return DevOpsCommand(
                command="kubectl rollout status deployment/<deployment_name> -n <namespace>",
                description="Check rollout status of a deployment (replace placeholders)",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 5 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl rollout history deployment/<deploy>"]
            )
        elif "restart" in user_input:
            return DevOpsCommand(
                command="kubectl rollout restart deployment/<deployment_name> -n <namespace>",
                description="Restart a deployment (replace placeholders)",
                command_type=CommandType.CONTAINER_MANAGEMENT,
                risk_level=RiskLevel.MEDIUM,
                requires_sudo=False,
                estimated_duration="< 30 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl patch deployment <deploy> -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"date\":\"`date +'%s'`\"}}}}}'"]
            )
        else:
            return DevOpsCommand(
                command="kubectl rollout history deployment/<deployment_name> -n <namespace>",
                description="Show rollout history of a deployment (replace placeholders)",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["kubectl"],
                alternative_commands=["kubectl rollout undo deployment/<deploy>"]
            )

    async def validate_command(
        self, command: DevOpsCommand, context: Dict[str, Any] = None
    ) -> bool:
        """Validate Kubernetes commands before execution"""
        # Check if kubectl is available
        if not shutil.which("kubectl"):
            self.logger.error("kubectl command not found in PATH")
            return False

        # Extract base kubectl command
        cmd_parts = command.command.split()
        if not cmd_parts or cmd_parts[0] != "kubectl":
            return False

        # Check for dangerous operations
        cmd_str = command.command.lower()
        for dangerous_cmd in self._dangerous_commands:
            if dangerous_cmd in cmd_str:
                self.logger.warning(f"Potentially dangerous Kubernetes command: {dangerous_cmd}")
                # Allow but flag as high risk
                if command.risk_level == RiskLevel.SAFE:
                    command.risk_level = RiskLevel.HIGH

        return True

    def get_help(self) -> str:
        """Return help text for the Kubernetes plugin"""
        return """
☸️ Kubernetes Plugin v1.0.0

This plugin provides Kubernetes cluster management commands.

Pod Operations:
• "get pods" / "list pods" / "show pods"
  → Show all pods across namespaces
  
• "pod logs <name>" / "logs <name>"
  → Display pod logs
  
• "describe pod <name>" / "pod details <name>"
  → Get detailed pod information
  
• "delete pod <name>"
  → Remove pod (⚠️ permanent)

Deployment Management:
• "get deployments" / "list deployments"
  → Show all deployments
  
• "scale deployment <name>" / "scale up/down <name>"
  → Scale deployment replicas
  
• "rollout status <name>" / "rollout restart <name>"
  → Manage deployment rollouts

Service Operations:
• "get services" / "list services"
  → Show all services
  
• "describe service <name>"
  → Get service details

Cluster Information:
• "get nodes" / "list nodes"
  → Show cluster nodes
  
• "get namespaces" / "list namespaces"
  → Show all namespaces
  
• "cluster info" / "cluster status"
  → Display cluster information
  
• "get all" / "cluster overview"
  → Overview of all resources
  
• "events" / "show events"
  → Recent cluster events

Examples:
  chatops ask "get all pods"
  chatops ask "show logs for nginx pod"
  chatops ask "scale deployment web to 3 replicas"
  chatops ask "cluster information"

⚠️ Note: Commands marked with placeholders like <pod_name> 
require you to replace them with actual values before execution.

🔧 Prerequisites: kubectl must be installed and configured
        """.strip()

    async def get_metrics(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get Kubernetes metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "kubectl_available": bool(shutil.which("kubectl")),
                "plugin_status": "active",
                "supported_operations": [
                    "pod_management", "deployment_management", "service_operations",
                    "namespace_management", "cluster_inspection", "resource_monitoring"
                ]
            }
        except Exception as e:
            self.logger.error(f"Error collecting Kubernetes metrics: {e}")
            return {"error": str(e)} 