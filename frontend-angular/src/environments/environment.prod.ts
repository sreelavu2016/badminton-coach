// These placeholders are replaced at CI/CD time by the Azure deployment pipeline
// after Bicep outputs the Container App FQDNs.
export const environment = {
  production: true,
  videoApiUrl: '__VIDEO_API_URL__/api/videos',
  analysisApiUrl: '__ANALYSIS_API_URL__/api/analysis',
};
