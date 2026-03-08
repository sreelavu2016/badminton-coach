// ============================================================
// AI Badminton Coach – Azure Infrastructure
// Deploys: ACR, PostgreSQL, Event Hubs (Kafka), Blob Storage,
//          Container Apps Environment + 3 apps, Static Web App
// ============================================================

targetScope = 'resourceGroup'

@description('Base name for all resources (lowercase, no spaces)')
param appName string = 'badmintoncoach'

@description('Azure region')
param location string = resourceGroup().location

@description('Environment tag (dev / staging / prod)')
param environment string = 'prod'

@description('PostgreSQL admin username')
param postgresAdminUser string = 'badmintonadmin'

@secure()
@description('PostgreSQL admin password (min 8 chars)')
param postgresAdminPassword string

@description('Container image tag to deploy')
param imageTag string = 'latest'

// ─── Variables ────────────────────────────────────────────────────────────────
var prefix = '${appName}${environment}'
var acrName = '${appName}acr${uniqueString(resourceGroup().id)}'
var tags = {
  application: 'ai-badminton-coach'
  environment: environment
}

// ─── Azure Container Registry ─────────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// ─── Storage Account + Blob Container ─────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${appName}stor${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource videosContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'videos'
  properties: {
    publicAccess: 'None'
  }
}

// ─── PostgreSQL Flexible Server ───────────────────────────────────────────────
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${prefix}-postgres'
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: { storageSizeGB: 32 }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgres
  name: 'allow-azure-services'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource badmintonDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgres
  name: 'badminton_db'
}

// ─── Event Hubs Namespace (Kafka protocol) ────────────────────────────────────
resource eventHubNamespace 'Microsoft.EventHub/namespaces@2023-01-01-preview' = {
  name: '${prefix}-eventhub'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    isAutoInflateEnabled: false
    kafkaEnabled: true
    zoneRedundant: false
  }
}

resource videoUploadedHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  parent: eventHubNamespace
  name: 'video-uploaded'
  properties: {
    messageRetentionInDays: 1
    partitionCount: 1
  }
}

resource aiConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2023-01-01-preview' = {
  parent: videoUploadedHub
  name: 'ai-analysis-group'
}

// ─── Log Analytics Workspace ───────────────────────────────────────────────────
resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ─── Container Apps Environment ────────────────────────────────────────────────
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${prefix}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logWorkspace.properties.customerId
        sharedKey: logWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// ─── Shared environment variables ─────────────────────────────────────────────
var postgresConnStr = 'jdbc:postgresql://${postgres.properties.fullyQualifiedDomainName}:5432/badminton_db?sslmode=require'
var kafkaBootstrap = '${eventHubNamespace.name}.servicebus.windows.net:9093'
var storageConnStr = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
var acrServer = acr.properties.loginServer

// ─── Video Service (Container App) ────────────────────────────────────────────
resource videoServiceApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${prefix}-video-svc'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8081
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      registries: [
        {
          server: acrServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'postgres-password', value: postgresAdminPassword }
        { name: 'storage-conn-str', value: storageConnStr }
        { name: 'eventhub-conn-str', value: listKeys('${eventHubNamespace.id}/authorizationRules/RootManageSharedAccessKey', eventHubNamespace.apiVersion).primaryConnectionString }
      ]
    }
    template: {
      containers: [
        {
          name: 'video-service'
          image: '${acrServer}/video-service:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'SPRING_DATASOURCE_URL', value: postgresConnStr }
            { name: 'SPRING_DATASOURCE_USERNAME', value: postgresAdminUser }
            { name: 'SPRING_DATASOURCE_PASSWORD', secretRef: 'postgres-password' }
            { name: 'SPRING_KAFKA_BOOTSTRAP_SERVERS', value: kafkaBootstrap }
            { name: 'SPRING_KAFKA_PROPERTIES_SECURITY_PROTOCOL', value: 'SASL_SSL' }
            { name: 'SPRING_KAFKA_PROPERTIES_SASL_MECHANISM', value: 'PLAIN' }
            { name: 'SPRING_KAFKA_PROPERTIES_SASL_JAAS_CONFIG', secretRef: 'eventhub-conn-str' }
            { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-conn-str' }
            { name: 'AZURE_STORAGE_CONTAINER_NAME', value: 'videos' }
            { name: 'APP_VIDEO_STORAGE_BACKEND', value: 'azure' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ─── Feedback Service (Container App) ─────────────────────────────────────────
resource feedbackServiceApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${prefix}-feedback-svc'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8082
        transport: 'auto'
      }
      registries: [
        {
          server: acrServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'postgres-password', value: postgresAdminPassword }
      ]
    }
    template: {
      containers: [
        {
          name: 'feedback-service'
          image: '${acrServer}/feedback-service:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'SPRING_DATASOURCE_URL', value: postgresConnStr }
            { name: 'SPRING_DATASOURCE_USERNAME', value: postgresAdminUser }
            { name: 'SPRING_DATASOURCE_PASSWORD', secretRef: 'postgres-password' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ─── AI Analysis Service (Container App) ──────────────────────────────────────
resource aiServiceApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${prefix}-ai-svc'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acrServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'storage-conn-str', value: storageConnStr }
        { name: 'eventhub-conn-str', value: listKeys('${eventHubNamespace.id}/authorizationRules/RootManageSharedAccessKey', eventHubNamespace.apiVersion).primaryConnectionString }
      ]
    }
    template: {
      containers: [
        {
          name: 'ai-analysis-service'
          image: '${acrServer}/ai-analysis-service:${imageTag}'
          resources: { cpu: json('2'), memory: '4Gi' }
          env: [
            { name: 'KAFKA_BOOTSTRAP_SERVERS', value: kafkaBootstrap }
            { name: 'KAFKA_SECURITY_PROTOCOL', value: 'SASL_SSL' }
            { name: 'KAFKA_SASL_MECHANISM', value: 'PLAIN' }
            { name: 'KAFKA_CONNECTION_STRING', secretRef: 'eventhub-conn-str' }
            { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-conn-str' }
            { name: 'AZURE_STORAGE_CONTAINER_NAME', value: 'videos' }
            { name: 'FEEDBACK_SERVICE_URL', value: 'http://${feedbackServiceApp.name}' }
            { name: 'VIDEO_STORAGE_BACKEND', value: 'azure' }
            { name: 'FRAME_SAMPLE_RATE', value: '5' }
            { name: 'MAX_VIDEO_DURATION_SECONDS', value: '60' }
            { name: 'MIN_POSE_CONFIDENCE', value: '0.5' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

// ─── Static Web App (Angular) ─────────────────────────────────────────────────
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: '${prefix}-frontend'
  location: 'eastus2'   // Static Web Apps only in specific regions
  tags: tags
  sku: { name: 'Free', tier: 'Free' }
  properties: {
    buildProperties: {
      appLocation: '/'
      outputLocation: 'dist/badminton-coach-frontend/browser'
      appBuildCommand: 'npm run build:prod'
    }
  }
}

// ─── Outputs ──────────────────────────────────────────────────────────────────
output acrLoginServer string = acr.properties.loginServer
output videoServiceUrl string = 'https://${videoServiceApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output eventHubNamespaceName string = eventHubNamespace.name
output storageAccountName string = storageAccount.name
