package cn.trunghuy.competition.config;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.repository.CompetitionRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Component
@ConditionalOnProperty(
        name = "competition.data-import.enabled",
        havingValue = "true",
        matchIfMissing = true
)
public class CompetitionDataImporter implements ApplicationRunner {

    private final CompetitionRepository competitionRepository;
    private final ObjectMapper objectMapper;
    private final Path dataFile;

    public CompetitionDataImporter(
            CompetitionRepository competitionRepository,
            ObjectMapper objectMapper,
            @Value("${competition.data-file}") String dataFile
    ) {
        this.competitionRepository = competitionRepository;
        this.objectMapper = objectMapper;
        this.dataFile = Path.of(dataFile);
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        if (competitionRepository.count() > 0 || !Files.exists(dataFile)) {
            return;
        }

        JsonNode root = objectMapper.readTree(dataFile);
        JsonNode items = root.path("competitions");
        List<Competition> competitions = new ArrayList<>();

        int order = 0;
        for (JsonNode node : items) {
            Competition item = new Competition();
            item.setId(text(node, "id"));
            item.setDisplayOrder(order++);
            item.setBrandId(text(node, "brand_id"));
            item.setName(text(node, "name"));
            item.setCategory(textList(node.path("category")));
            item.setTags(textList(node.path("tags")));
            item.setLevel(text(node, "level"));
            item.setKind(text(node, "kind"));
            item.setInfoChannel(text(node, "info_channel"));
            item.setOrganizer(text(node, "organizer"));
            item.setLink(text(node, "link"));
            item.setDescription(text(node, "description"));
            item.setEligibility(text(node, "eligibility"));
            item.setHasCampusNotice(bool(node, "has_campus_notice"));
            item.setActive(bool(node, "active"));
            item.setEdition(text(node, "edition"));
            item.setTrackId(text(node, "track_id"));
            item.setPublishedAt(date(node, "published_at"));
            item.setRegistrationStart(date(node, "registration_start"));
            item.setRegistrationEnd(date(node, "registration_end"));
            item.setCompetitionStart(date(node, "competition_start"));
            item.setCompetitionEnd(date(node, "competition_end"));
            item.setLastChecked(date(node, "last_checked"));
            item.setNeedsReview(bool(node, "needs_review"));
            item.setStatusOverride(text(node, "status_override"));
            item.setScheduleSource(text(node, "schedule_source"));
            item.setScheduleConfidence(text(node, "schedule_confidence"));
            item.setLinkKind(text(node, "link_kind"));
            item.setRegistrationStartEstimated(date(node, "registration_start_estimated"));
            item.setRegistrationEndEstimated(date(node, "registration_end_estimated"));
            competitions.add(item);
        }

        competitionRepository.saveAll(competitions);
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
}
