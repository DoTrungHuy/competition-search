package cn.trunghuy.competition;

import cn.trunghuy.competition.repository.CompetitionRepository;
import cn.trunghuy.competition.service.CompetitionSyncService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import tools.jackson.databind.ObjectMapper;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class CompetitionSyncServiceTests {

    @Autowired
    private CompetitionSyncService competitionSyncService;

    @Autowired
    private CompetitionRepository competitionRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void replaceAllReplacesExistingRows() throws Exception {
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
        competitionSyncService.replaceAll(objectMapper.readTree(first));
        assertThat(competitionRepository.count()).isEqualTo(2);

        String second = """
                {
                  "competitions": [
                    {
                      "id": "sync-c",
                      "name": "C",
                      "category": ["后端"],
                      "tags": ["Spring Boot"]
                    }
                  ]
                }
                """;
        competitionSyncService.replaceAll(objectMapper.readTree(second));

        assertThat(competitionRepository.count()).isEqualTo(1);
        assertThat(competitionRepository.findById("sync-a")).isEmpty();
        assertThat(competitionRepository.findById("sync-c")).isPresent();
    }
}
