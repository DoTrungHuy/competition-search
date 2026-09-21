package cn.trunghuy.competition;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.entity.ReviewCandidate;
import cn.trunghuy.competition.repository.CompetitionRepository;
import cn.trunghuy.competition.repository.ReviewCandidateRepository;
import cn.trunghuy.competition.service.CompetitionSyncService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class CompetitionSyncServiceTests {

    @Autowired
    private CompetitionSyncService competitionSyncService;

    @Autowired
    private CompetitionRepository competitionRepository;

    @Autowired
    private ReviewCandidateRepository reviewCandidateRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void cleanUp() {
        reviewCandidateRepository.deleteAll();
        competitionRepository.deleteAll();
    }

    @Test
    void syncUpsertsWithoutDeletingRowsMissingFromFeed() throws Exception {
        String first = """
                {
                  "competitions": [
                    {
                      "id": "sync-a",
                      "name": "A",
                      "category": ["算法"],
                      "tags": ["Java"]
                    },
                    {
                      "id": "sync-b",
                      "name": "B",
                      "category": [],
                      "tags": []
                    }
                  ]
                }
                """;
        competitionSyncService.sync(objectMapper.readTree(first));
        assertThat(competitionRepository.count()).isEqualTo(2);

        String second = """
                {
                  "competitions": [
                    {
                      "id": "sync-b",
                      "name": "B updated",
                      "category": ["后端"],
                      "tags": ["Spring Boot"]
                    }
                  ]
                }
                """;
        competitionSyncService.sync(objectMapper.readTree(second));

        assertThat(competitionRepository.count()).isEqualTo(2);
        assertThat(competitionRepository.findById("sync-a")).isPresent();
        assertThat(competitionRepository.findById("sync-b"))
                .get()
                .extracting(Competition::getName)
                .isEqualTo("B updated");
    }

    @Test
    void syncDoesNotOverwriteManuallyReviewedCompetition() throws Exception {
        Competition manual = new Competition();
        manual.setId("manual");
        manual.setName("人工版本");
        manual.setDisplayOrder(0);
        manual.setNeedsReview(false);
        competitionRepository.saveAndFlush(manual);

        ReviewCandidate candidate = new ReviewCandidate();
        candidate.setId("manual");
        candidate.setName("人工版本");
        candidate.setReviewStatus("APPROVED");
        candidate.setRawData("{\"id\":\"manual\",\"name\":\"人工版本\"}");
        candidate.setCreatedAt(LocalDateTime.now());
        candidate.setUpdatedAt(LocalDateTime.now());
        reviewCandidateRepository.saveAndFlush(candidate);

        String feed = """
                {
                  "competitions": [
                    {
                      "id": "manual",
                      "name": "自动旧版本"
                    },
                    {
                      "id": "automatic",
                      "name": "自动新增"
                    }
                  ]
                }
                """;

        int synced = competitionSyncService.sync(objectMapper.readTree(feed));

        assertThat(synced).isEqualTo(1);
        assertThat(competitionRepository.findById("manual"))
                .get()
                .extracting(Competition::getName)
                .isEqualTo("人工版本");
        assertThat(competitionRepository.findById("automatic")).isPresent();
    }
}
