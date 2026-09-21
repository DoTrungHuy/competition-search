package cn.trunghuy.competition;

import cn.trunghuy.competition.entity.ReviewCandidate;
import cn.trunghuy.competition.repository.ReviewCandidateRepository;
import cn.trunghuy.competition.service.ReviewCandidateSyncService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import tools.jackson.databind.ObjectMapper;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class ReviewCandidateSyncServiceTests {

    @Autowired
    private ReviewCandidateSyncService reviewCandidateSyncService;

    @Autowired
    private ReviewCandidateRepository reviewCandidateRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void syncCreatesAndRemovesPendingCandidates() throws Exception {
        String first = """
                {
                  "pending": [
                    {
                      "id": "review-a",
                      "name": "Candidate A",
                      "link": "https://example.com/a",
                      "source_list": "campus",
                      "source_list_name": "Campus"
                    },
                    {
                      "id": "review-b",
                      "name": "Candidate B",
                      "source_list": "devpost"
                    }
                  ]
                }
                """;

        assertThat(reviewCandidateSyncService.sync(objectMapper.readTree(first))).isEqualTo(2);
        assertThat(reviewCandidateRepository.count()).isEqualTo(2);

        ReviewCandidate candidate = reviewCandidateRepository.findById("review-a").orElseThrow();
        assertThat(candidate.getReviewStatus()).isEqualTo("PENDING");
        assertThat(candidate.getSource()).isEqualTo("campus");
        assertThat(candidate.getRawData()).contains("Candidate A");

        String second = """
                {
                  "pending": [
                    {
                      "id": "review-b",
                      "name": "Candidate B updated",
                      "source_list": "devpost"
                    }
                  ]
                }
                """;

        assertThat(reviewCandidateSyncService.sync(objectMapper.readTree(second))).isEqualTo(1);
        assertThat(reviewCandidateRepository.findById("review-a")).isEmpty();
        assertThat(reviewCandidateRepository.findById("review-b"))
                .get()
                .extracting(ReviewCandidate::getName)
                .isEqualTo("Candidate B updated");
    }
}
