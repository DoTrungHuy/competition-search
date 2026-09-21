package cn.trunghuy.competition.config;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.repository.CompetitionRepository;
import cn.trunghuy.competition.service.CompetitionJsonMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
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
    private final CompetitionJsonMapper competitionJsonMapper;
    private final Path dataFile;

    public CompetitionDataImporter(
            CompetitionRepository competitionRepository,
            ObjectMapper objectMapper,
            CompetitionJsonMapper competitionJsonMapper,
            @Value("${competition.data-file}") String dataFile
    ) {
        this.competitionRepository = competitionRepository;
        this.objectMapper = objectMapper;
        this.competitionJsonMapper = competitionJsonMapper;
        this.dataFile = Path.of(dataFile);
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        if (competitionRepository.count() > 0 || !Files.exists(dataFile)) {
            return;
        }

        JsonNode root = objectMapper.readTree(dataFile);
        List<Competition> competitions = competitionJsonMapper.fromRoot(root);

        competitionRepository.saveAll(competitions);
    }
}
