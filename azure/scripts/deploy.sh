#!/usr/bin/env bash
# =============================================================================
# AI Badminton Coach – One-command Azure deployment
# Usage:
#   export POSTGRES_PASSWORD="YourStr0ngP@ssword"
#   bash azure/scripts/deploy.sh
#
# Prerequisites: Azure CLI (az) logged in, Docker running
# =============================================================================
set -euo pipefail

# ── Config (override via env) ─────────────────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-badminton-coach}"
LOCATION="${LOCATION:-australiaeast}"
APP_NAME="${APP_NAME:-badmintoncoach}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD env var}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================================"
echo "  AI Badminton Coach – Azure Deployment"
echo "  Resource Group : ${RESOURCE_GROUP}"
echo "  Location       : ${LOCATION}"
echo "  App Name       : ${APP_NAME}"
echo "  Image Tag      : ${IMAGE_TAG}"
echo "========================================================"

# ── 1. Create resource group ──────────────────────────────────────────────────
echo ""
echo ">>> [1/5] Creating resource group..."
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output table

# ── 2. Deploy Bicep infrastructure ────────────────────────────────────────────
echo ""
echo ">>> [2/5] Deploying Azure infrastructure (Bicep)..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${PROJECT_ROOT}/azure/bicep/main.bicep" \
  --parameters \
      appName="${APP_NAME}" \
      environment=prod \
      postgresAdminPassword="${POSTGRES_PASSWORD}" \
      imageTag="${IMAGE_TAG}" \
  --query "properties.outputs" \
  --output json)

ACR_SERVER=$(echo "${DEPLOY_OUTPUT}" | jq -r '.acrLoginServer.value')
VIDEO_SVC_URL=$(echo "${DEPLOY_OUTPUT}" | jq -r '.videoServiceUrl.value')
FRONTEND_URL=$(echo "${DEPLOY_OUTPUT}" | jq -r '.frontendUrl.value')
STORAGE_ACCOUNT=$(echo "${DEPLOY_OUTPUT}" | jq -r '.storageAccountName.value')

echo "  ACR Server      : ${ACR_SERVER}"
echo "  Video Svc URL   : ${VIDEO_SVC_URL}"
echo "  Frontend URL    : ${FRONTEND_URL}"
echo "  Storage Account : ${STORAGE_ACCOUNT}"

# ── 3. Build & push Docker images ─────────────────────────────────────────────
echo ""
echo ">>> [3/5] Building and pushing Docker images to ACR..."
az acr login --name "${ACR_SERVER%%.*}"

for SERVICE in video-service feedback-service ai-analysis-service; do
  case "${SERVICE}" in
    video-service)    CONTEXT="${PROJECT_ROOT}/backend-video-service" ;;
    feedback-service) CONTEXT="${PROJECT_ROOT}/backend-feedback-service" ;;
    ai-analysis-service) CONTEXT="${PROJECT_ROOT}/ai-analysis-service" ;;
  esac

  IMAGE="${ACR_SERVER}/${SERVICE}:${IMAGE_TAG}"
  echo "  Building ${IMAGE}..."
  docker build -t "${IMAGE}" "${CONTEXT}"
  docker push "${IMAGE}"
done

# ── 4. Build & deploy Angular frontend ────────────────────────────────────────
echo ""
echo ">>> [4/5] Building Angular frontend..."

ENV_PROD_FILE="${PROJECT_ROOT}/frontend-angular/src/environments/environment.prod.ts"
cp "${ENV_PROD_FILE}" "${ENV_PROD_FILE}.bak"

# Substitute placeholder URLs
ANALYSIS_URL="${VIDEO_SVC_URL/video-svc/feedback-svc}"
sed -i.tmp \
  -e "s|__VIDEO_API_URL__|${VIDEO_SVC_URL}|g" \
  -e "s|__ANALYSIS_API_URL__|${ANALYSIS_URL}|g" \
  "${ENV_PROD_FILE}"

(cd "${PROJECT_ROOT}/frontend-angular" && npm ci --silent && npm run build:prod)

# Restore original placeholder file
mv "${ENV_PROD_FILE}.bak" "${ENV_PROD_FILE}"
rm -f "${ENV_PROD_FILE}.tmp"

# Get Static Web App API token and deploy
SWA_NAME="${APP_NAME}prod-frontend"
SWA_TOKEN=$(az staticwebapp secrets list \
  --name "${SWA_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "properties.apiKey" \
  --output tsv 2>/dev/null || echo "")

if [ -n "${SWA_TOKEN}" ]; then
  npx --yes @azure/static-web-apps-cli deploy \
    "${PROJECT_ROOT}/frontend-angular/dist/badminton-coach-frontend/browser" \
    --deployment-token "${SWA_TOKEN}" \
    --env production
  echo "  Frontend deployed to: ${FRONTEND_URL}"
else
  echo "  WARNING: Could not retrieve Static Web App token."
  echo "  Deploy manually via GitHub Actions or Azure Portal."
fi

# ── 5. Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "  Deployment complete!"
echo ""
echo "  Frontend  : ${FRONTEND_URL}"
echo "  Video API : ${VIDEO_SVC_URL}"
echo ""
echo "  Next steps:"
echo "  1. Set AZURE_STATIC_WEB_APP_TOKEN secret in GitHub"
echo "     az staticwebapp secrets list --name ${SWA_NAME} -g ${RESOURCE_GROUP}"
echo "  2. Set AZURE_CREDENTIALS secret (service principal JSON)"
echo "  3. Push to main branch to trigger CI/CD"
echo "========================================================"
