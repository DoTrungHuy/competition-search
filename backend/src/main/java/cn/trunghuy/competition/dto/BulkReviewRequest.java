package cn.trunghuy.competition.dto;

import java.util.List;

public record BulkReviewRequest(List<String> ids, String note) {
}
