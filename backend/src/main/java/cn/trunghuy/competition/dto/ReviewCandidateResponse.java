package cn.trunghuy.competition.dto;

import tools.jackson.databind.JsonNode;

import java.time.LocalDateTime;

public record ReviewCandidateResponse(
        String id,
        String name,
        String link,
        String source,
        String sourceName,
        String aiVerdict,
        String aiConfidence,
        String aiReason,
        String reviewStatus,
        JsonNode rawData,
        LocalDateTime createdAt,
        LocalDateTime updatedAt,
        LocalDateTime reviewedAt,
        String reviewNote
) {
}
