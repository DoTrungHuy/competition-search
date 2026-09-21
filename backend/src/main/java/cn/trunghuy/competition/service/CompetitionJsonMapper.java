package cn.trunghuy.competition.service;

import cn.trunghuy.competition.entity.Competition;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Component
public class CompetitionJsonMapper {

    public List<Competition> fromRoot(JsonNode root) {
        JsonNode items = root.path("competitions");
        List<Competition> competitions = new ArrayList<>();

        int order = 0;
        for (JsonNode node : items) {
            competitions.add(fromNode(node, order++));
        }

        return competitions;
    }

    public Competition fromNode(JsonNode node, int displayOrder) {
        Competition item = new Competition();
        item.setId(text(node, "id"));
        item.setDisplayOrder(displayOrder);
        applyPresentFields(node, item);
        return item;
    }

    public void mergeInto(JsonNode node, Competition item) {
        applyPresentFields(node, item);
    }

    private void applyPresentFields(JsonNode node, Competition item) {
        setTextIfPresent(node, "brand_id", item::setBrandId);
        setTextIfPresent(node, "name", item::setName);
        if (node.has("category") && !node.get("category").isNull()) {
            item.setCategory(textList(node.path("category")));
        }
        if (node.has("tags") && !node.get("tags").isNull()) {
            item.setTags(textList(node.path("tags")));
        }
        setTextIfPresent(node, "level", item::setLevel);
        setTextIfPresent(node, "kind", item::setKind);
        setTextIfPresent(node, "info_channel", item::setInfoChannel);
        setTextIfPresent(node, "organizer", item::setOrganizer);
        setTextIfPresent(node, "link", item::setLink);
        setTextIfPresent(node, "description", item::setDescription);
        setTextIfPresent(node, "eligibility", item::setEligibility);
        setBoolIfPresent(node, "has_campus_notice", item::setHasCampusNotice);
        setBoolIfPresent(node, "active", item::setActive);
        setTextIfPresent(node, "edition", item::setEdition);
        setTextIfPresent(node, "track_id", item::setTrackId);
        setDateIfPresent(node, "published_at", item::setPublishedAt);
        setDateIfPresent(node, "registration_start", item::setRegistrationStart);
        setDateIfPresent(node, "registration_end", item::setRegistrationEnd);
        setDateIfPresent(node, "competition_start", item::setCompetitionStart);
        setDateIfPresent(node, "competition_end", item::setCompetitionEnd);
        setDateIfPresent(node, "last_checked", item::setLastChecked);
        setBoolIfPresent(node, "needs_review", item::setNeedsReview);
        setTextIfPresent(node, "status_override", item::setStatusOverride);
        setTextIfPresent(node, "schedule_source", item::setScheduleSource);
        setTextIfPresent(node, "schedule_confidence", item::setScheduleConfidence);
        setTextIfPresent(node, "link_kind", item::setLinkKind);
        setDateIfPresent(node, "registration_start_estimated", item::setRegistrationStartEstimated);
        setDateIfPresent(node, "registration_end_estimated", item::setRegistrationEndEstimated);
    }

    private String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? null : value.asText();
    }

    private Boolean bool(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? null : value.asBoolean();
    }

    private LocalDate date(JsonNode node, String field) {
        String value = text(node, field);
        return value == null || value.isBlank() ? null : LocalDate.parse(value);
    }

    private List<String> textList(JsonNode node) {
        if (node == null || !node.isArray()) {
            return new ArrayList<>();
        }
        List<String> values = new ArrayList<>();
        node.forEach(value -> values.add(value.asText()));
        return values;
    }

    private void setTextIfPresent(
            JsonNode node,
            String field,
            java.util.function.Consumer<String> setter
    ) {
        if (node.has(field) && !node.get(field).isNull()) {
            setter.accept(node.get(field).asText());
        }
    }

    private void setBoolIfPresent(
            JsonNode node,
            String field,
            java.util.function.Consumer<Boolean> setter
    ) {
        if (node.has(field) && !node.get(field).isNull()) {
            setter.accept(node.get(field).asBoolean());
        }
    }

    private void setDateIfPresent(
            JsonNode node,
            String field,
            java.util.function.Consumer<LocalDate> setter
    ) {
        if (node.has(field) && !node.get(field).isNull()) {
            String value = node.get(field).asText();
            setter.accept(value.isBlank() ? null : LocalDate.parse(value));
        }
    }
}
