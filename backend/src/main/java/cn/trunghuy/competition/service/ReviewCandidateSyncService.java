package cn.trunghuy.competition.service;

import cn.trunghuy.competition.entity.ReviewCandidate;
import cn.trunghuy.competition.repository.ReviewCandidateRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Set;

@Service
public class ReviewCandidateSyncService {

    private static final String PENDING = "PENDING";

    private final ReviewCandidateRepository reviewCandidateRepository;
    private final ObjectMapper objectMapper;

    public ReviewCandidateSyncService(
            ReviewCandidateRepository reviewCandidateRepository,
            ObjectMapper objectMapper
    ) {
        this.reviewCandidateRepository = reviewCandidateRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public int sync(JsonNode root) {
        JsonNode pending = root.path("pending");
        Set<String> incomingIds = new HashSet<>();
        LocalDateTime now = LocalDateTime.now();

        for (JsonNode node : pending) {
            String id = text(node, "id");
            if (id == null || id.isBlank()) {
                continue;
            }

            incomingIds.add(id);
            ReviewCandidate candidate = reviewCandidateRepository.findById(id)
                    .orElseGet(ReviewCandidate::new);
            boolean isNew = candidate.getId() == null;

            candidate.setId(id);
            candidate.setName(requiredText(node, "name", id));
            candidate.setLink(text(node, "link"));
            candidate.setSource(text(node, "source_list"));
            candidate.setSourceName(text(node, "source_list_name"));
            candidate.setAiVerdict(text(node, "ai_verdict"));
            candidate.setAiConfidence(text(node, "ai_confidence"));
            candidate.setAiReason(text(node, "ai_reason"));
            if (isNew || candidate.getReviewStatus() == null) {
                candidate.setReviewStatus(PENDING);
            }
            candidate.setRawData(toJson(node));
            if (isNew || candidate.getCreatedAt() == null) {
                candidate.setCreatedAt(now);
            }
            candidate.setUpdatedAt(now);
            reviewCandidateRepository.save(candidate);
        }

        for (ReviewCandidate candidate : reviewCandidateRepository.findAllByReviewStatus(PENDING)) {
            if (!incomingIds.contains(candidate.getId())) {
                reviewCandidateRepository.delete(candidate);
            }
        }

        reviewCandidateRepository.flush();
        return incomingIds.size();
    }

    private String requiredText(JsonNode node, String field, String id) {
        String value = text(node, field);
        return value == null || value.isBlank() ? id : value;
    }

    private String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? null : value.asText();
    }

    private String toJson(JsonNode node) {
        try {
            return objectMapper.writeValueAsString(node);
        } catch (JacksonException error) {
            throw new IllegalArgumentException("Unable to serialize review candidate", error);
        }
    }
}
