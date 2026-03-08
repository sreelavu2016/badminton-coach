package com.badminton.video.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import jakarta.annotation.PostConstruct;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Configuration
public class StorageConfig {

    @Value("${app.video-storage-path:./storage/videos}")
    private String storagePath;

    @Value("${app.video-storage-backend:local}")
    private String storageBackend;

    @Value("${azure.storage.connection-string:}")
    private String azureConnectionString;

    @Value("${azure.storage.container-name:videos}")
    private String azureContainerName;

    @PostConstruct
    public void init() throws Exception {
        if ("local".equalsIgnoreCase(storageBackend)) {
            Path path = Paths.get(storagePath);
            if (!Files.exists(path)) {
                Files.createDirectories(path);
            }
        }
    }

    public String getStoragePath() { return storagePath; }
    public String getStorageBackend() { return storageBackend; }
    public String getAzureConnectionString() { return azureConnectionString; }
    public String getAzureContainerName() { return azureContainerName; }
    public boolean isAzureBackend() { return "azure".equalsIgnoreCase(storageBackend); }
}
