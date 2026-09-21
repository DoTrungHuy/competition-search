package cn.trunghuy.competition.service;

import cn.trunghuy.competition.dto.ReviewCandidateResponse;
import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.entity.ReviewCandidate;
import cn.trunghuy.competition.repository.CompetitionRepository;
import cn.trunghuy.competition.repository.ReviewCandidateRepository;
import jakarta.transaction.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;

@Service
public class AdminReviewService {

    private static final String PENDING = "PENDING";
    private static final String APPROVED = "APPROVED";
    private static final String REJECTED = "REJECTED";

    private final ReviewCandidateRepository reviewCandidateRepository;
    private final CompetitionRepository competitionRepository;
    private final CompetitionJsonMapper competitionJsonMapper;
    private final ObjectMapper objectMapper;

    public AdminReviewService(
            ReviewCandidateRepository reviewCandidateRepository,
            CompetitionRepository competitionRepository,
            CompetitionJsonMapper competitionJsonMapper,
            ObjectMapper objectMapper
    ) {
        this.reviewCandidateRepository = reviewCandidateRepository;
        this.competitionRepository = competitionRepository;
        this.competitionJsonMapper = competitionJsonMapper;
        this.objectMapper = objectMapper;
    }

    public List<ReviewCandidateResponse> findAll(String status) {
        String normalized = normalizeStatus(status == null ? PENDING : status);
        return reviewCandidateRepository
                .findAllByReviewStatusOrderByUpdatedAtDesc(normalized)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    public ReviewCandidateResponse findById(String id) {
        return toResponse(requireCandidate(id));
    }

    @Transactional
    public ReviewCandidateResponse approve(String id, String note) {
        ReviewCandidate candidate = requirePending(id);
        JsonNode raw = parseRaw(candidate);

        Competition competition = competitionRepository.findById(id)
                .orElseGet(() -> {
                    Competition created = new Competition();
                    created.setId(id);
                    created.setDisplayOrder(competitionRepository.findMaxDisplayOrder() + 1);
                    return created;
                });

        competitionJsonMapper.mergeInto(raw, competition);
        if (competition.getName() == null || competition.getName().isBlank()) {
            competition.setName(candidate.getName());
        }
        competition.setNeedsReview(false);
        competitionRepository.saveAndFlush(competition);

        markReviewed(candidate, APPROVED, note);
        return toResponse(candidate);
    }

    @Transactional
    public ReviewCandidateResponse reject(String id, String note) {
        ReviewCandidate candidate = requirePending(id);
        markReviewed(candidate, REJECTED, note);
        return toResponse(candidate);
    }

    private void markReviewed(ReviewCandidate candidate, String status, String note) {
        LocalDateTime now = LocalDateTime.now();
        candidate.setReviewStatus(status);
        candidate.setReviewNote(note == null || note.isBlank() ? null : note.trim());
        candidate.setReviewedAt(now);
        candidate.setUpdatedAt(now);
        reviewCandidateRepository.saveAndFlush(candidate);
    }

    private ReviewCandidate requireCandidate(String id) {
        return reviewCandidateRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Review candidate not found: " + id
                ));
    }

    private ReviewCandidate requirePending(String id) {
        ReviewCandidate candidate = requireCandidate(id);
        if (!PENDING.equals(candidate.getReviewStatus())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Review candidate is already " + candidate.getReviewStatus()
            );
        }
        return candidate;
    }

    private String normalizeStatus(String status) {
        String normalized = status.trim().toUpperCase(Locale.ROOT);
        if (!List.of(PENDING, APPROVED, REJECTED).contains(normalized)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "status must be PENDING, APPROVED or REJECTED"
            );
        }
        return normalized;
    }

    private JsonNode parseRaw(ReviewCandidate candidate) {
        try {
            return objectMapper.readTree(candidate.getRawData());
        } catch (JacksonException error) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Stored candidate JSON is invalid"
            );
        }
    }

    private ReviewCandidateResponse toResponse(ReviewCandidate candidate) {
        JsonNode raw = parseRaw(candidate);
        return new ReviewCandidateResponse(
                candidate.getId(),
                candidate.getName(),
                candidate.getLink(),
                candidate.getSource(),
                candidate.getSourceName(),
                candidate.getAiVerdict(),
                candidate.getAiConfidence(),
                candidate.getAiReason(),
                candidate.getReviewStatus(),
                raw,
                candidate.getCreatedAt(),
                candidate.getUpdatedAt(),
                candidate.getReviewedAt(),
                candidate.getReviewNote()
        );
    }
}
