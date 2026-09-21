package cn.trunghuy.competition;

import cn.trunghuy.competition.dto.ReviewCandidateResponse;
import cn.trunghuy.competition.entity.ReviewCandidate;
import cn.trunghuy.competition.repository.CompetitionRepository;
import cn.trunghuy.competition.repository.ReviewCandidateRepository;
import cn.trunghuy.competition.service.AdminReviewService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import tools.jackson.databind.ObjectMapper;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class AdminReviewServiceTests {

    @Autowired
    private AdminReviewService adminReviewService;

    @Autowired
    private ReviewCandidateRepository reviewCandidateRepository;

    @Autowired
    private CompetitionRepository competitionRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void cleanUp() {
        reviewCandidateRepository.deleteAll();
        competitionRepository.deleteAll();
    }

    @Test
    void approveCreatesCompetitionAndAppliesManualEdits() throws Exception {
        saveCandidate(
                "approve-me",
                "测试通过竞赛",
                """
                {
                  "id": "approve-me",
                  "name": "测试通过竞赛",
                  "kind": "全国赛事",
                  "link": "https://example.com/approve",
                  "description": "candidate description",
                  "needs_review": true
                }
                """
        );

        ReviewCandidateResponse response = adminReviewService.approve(
                "approve-me",
                "人工确认有效",
                objectMapper.readTree("""
                        {
                          "name": "人工修改后的名称",
                          "level": "国家级"
                        }
                        """)
        );

        assertThat(response.reviewStatus()).isEqualTo("APPROVED");
        assertThat(response.reviewNote()).isEqualTo("人工确认有效");
        assertThat(response.reviewedAt()).isNotNull();

        var competition = competitionRepository.findById("approve-me").orElseThrow();
        assertThat(competition.getName()).isEqualTo("人工修改后的名称");
        assertThat(competition.getKind()).isEqualTo("全国赛事");
        assertThat(competition.getLevel()).isEqualTo("国家级");
        assertThat(competition.getNeedsReview()).isFalse();
    }

    @Test
    void rejectDoesNotCreateCompetition() {
        saveCandidate(
                "reject-me",
                "测试拒绝竞赛",
                """
                {
                  "id": "reject-me",
                  "name": "测试拒绝竞赛",
                  "link": "https://example.com/reject"
                }
                """
        );

        ReviewCandidateResponse response = adminReviewService.reject("reject-me", "不是有效赛事");

        assertThat(response.reviewStatus()).isEqualTo("REJECTED");
        assertThat(response.reviewNote()).isEqualTo("不是有效赛事");
        assertThat(competitionRepository.findById("reject-me")).isEmpty();
    }

    private void saveCandidate(String id, String name, String rawData) {
        LocalDateTime now = LocalDateTime.now();
        ReviewCandidate candidate = new ReviewCandidate();
        candidate.setId(id);
        candidate.setName(name);
        candidate.setReviewStatus("PENDING");
        candidate.setRawData(rawData);
        candidate.setCreatedAt(now);
        candidate.setUpdatedAt(now);
        reviewCandidateRepository.saveAndFlush(candidate);
    }
}
