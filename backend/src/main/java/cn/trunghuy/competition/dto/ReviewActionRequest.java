package cn.trunghuy.competition.dto;

import tools.jackson.databind.JsonNode;

public record ReviewActionRequest(String note, JsonNode data) {
}
