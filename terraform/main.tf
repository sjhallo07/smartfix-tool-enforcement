module "smartfix_tool_enforcement" {
	source = "github.com/sjhallo07/smartfix-tool-enforcement/terraform/ibm-cloud"

	project_name = "smartfix-tool-enforcement"
	environment  = "alpha"
	region       = "us-south"
	# Configuración de recursos
	kubernetes_cluster_name = "smartfix-tool-enforcement-cluster"
	db_instance_name        = "smartfix-tool-enforcement-db"
}
