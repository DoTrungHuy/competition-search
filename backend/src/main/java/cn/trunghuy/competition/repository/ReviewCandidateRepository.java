package cn.trunghuy.competition.repository;

import cn.trunghuy.competition.entity.ReviewCandidate;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReviewCandidateRepository extends JpaRepository<ReviewCandidate, String> {
    List<ReviewCandidate> findAllByReviewStatus(String reviewStatus);
}
