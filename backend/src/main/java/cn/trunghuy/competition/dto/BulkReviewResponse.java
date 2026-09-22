package cn.trunghuy.competition.dto;

import java.util.List;

public record BulkReviewResponse(
        String status,
        int approved,
        List<String> ids
) {
}
