# Default terraform variables for single-project stack
project_id       = "your-gcp-project-id"
project_name     = "enterprise-agent-service"
region           = "europe-west2"
repository_owner = "your-org"
repository_name  = "enterprise-agent-blueprint"
tf_state_bucket  = "your-gcp-project-id-tfstate"

# BigQuery & Lakehouse
bq_dataset_id              = "lakehouse_sharing"
lakehouse_hydrated         = false
user_entitlements_table_id = "user_entitlements"
marketing_dataset_id       = "enterprise_marketing_studio"
campaign_index_table_id    = "campaigns_index"

# A2UI Frontend
a2ui_iframe_domain        = "a2ui.example.com"
a2ui_iframe_auth_mode     = "iap"
a2ui_iframe_allowed_cidrs = []
a2ui_iframe_iap_members   = ["group:enterprise-users@example.com"]

# Agent Users & Admins
finance_agent_user_members  = ["group:finance-analysts@example.com"]
pilot_retail_user_members   = ["group:branch-staff@example.com"]
finance_agent_admin_members = ["group:agent-admins@example.com"]
