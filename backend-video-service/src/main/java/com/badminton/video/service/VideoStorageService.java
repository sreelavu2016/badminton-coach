package com.badminton.video.service;

import com.azure.storage.blob.BlobClient;
import com.azure.storage.blob.BlobContainerClient;
import com.azure.storage.blob.BlobServiceClient;
import com.azure.storage.blob.BlobServiceClientBuilder;
import com.badminton.video.config.StorageConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

@Service
@RequiredArgsConstructor
@Slf4j
public class VideoStorageService {

    private final StorageConfig storageConfig;

    // ── Upload ────────────────────────────────────────────────────────────────

    public String storeVideo(String videoId, MultipartFile file) throws IOException {
        String extension = getExtension(file.getOriginalFilename());
        String blobName = videoId + "." + extension;

        if (storageConfig.isAzureBackend()) {
            return storeToAzure(blobName, file);
        } else {
            return storeToLocal(blobName, file);
        }
    }

    private String storeToLocal(String filename, MultipartFile file) throws IOException {
        Path targetPath = Paths.get(storageConfig.getStoragePath()).resolve(filename);
        Files.copy(file.getInputStream(), targetPath, StandardCopyOption.REPLACE_EXISTING);
        log.info("Stored video locally at {}", targetPath);
        return "storage/videos/" + filename;
    }

    private String storeToAzure(String blobName, MultipartFile file) throws IOException {
        BlobContainerClient container = getBlobContainer();
        BlobClient blob = container.getBlobClient(blobName);
        blob.upload(file.getInputStream(), file.getSize(), true);
        String url = blob.getBlobUrl();
        log.info("Stored video in Azure Blob: {}", url);
        return url;
    }

    // ── Stream ────────────────────────────────────────────────────────────────

    /** Opens an InputStream for the video, works for both backends. */
    public InputStream openVideoStream(String videoUrl) throws IOException {
        if (storageConfig.isAzureBackend()) {
            BlobClient blob = getBlobByUrl(videoUrl);
            return blob.openInputStream();
        } else {
            return Files.newInputStream(Paths.get(videoUrl));
        }
    }

    /** Returns the local Path (only valid for local backend). */
    public Path getVideoPath(String videoUrl) {
        return Paths.get(videoUrl);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private BlobContainerClient getBlobContainer() {
        BlobServiceClient serviceClient = new BlobServiceClientBuilder()
                .connectionString(storageConfig.getAzureConnectionString())
                .buildClient();
        return serviceClient.getBlobContainerClient(storageConfig.getAzureContainerName());
    }

    private BlobClient getBlobByUrl(String blobUrl) {
        BlobContainerClient container = getBlobContainer();
        String blobName = blobUrl.substring(blobUrl.lastIndexOf('/') + 1);
        return container.getBlobClient(blobName);
    }

    private String getExtension(String filename) {
        if (filename == null || !filename.contains(".")) {
            return "mp4";
        }
        return filename.substring(filename.lastIndexOf('.') + 1).toLowerCase();
    }
}
