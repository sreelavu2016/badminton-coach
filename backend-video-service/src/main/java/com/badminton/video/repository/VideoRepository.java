package com.badminton.video.repository;

import com.badminton.video.model.Video;
import com.badminton.video.model.VideoStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface VideoRepository extends JpaRepository<Video, String> {
    List<Video> findByUserId(String userId);
    List<Video> findByStatus(VideoStatus status);
}
