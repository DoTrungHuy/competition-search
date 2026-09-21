package cn.trunghuy.competition.service;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.repository.CompetitionRepository;
import cn.trunghuy.competition.repository.ReviewCandidateRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class CompetitionSyncService {

    private final CompetitionRepository competitionRepository;
    private final ReviewCandidateRepository reviewCandidateRepository;
    private final CompetitionJsonMapper competitionJsonMapper;

    public CompetitionSyncService(
            CompetitionRepository competitionRepository,
            ReviewCandidateRepository reviewCandidateRepository,
            CompetitionJsonMapper competitionJsonMapper
    ) {
        this.competitionRepository = competitionRepository;
        this.reviewCandidateRepository = reviewCandidateRepository;
        this.competitionJsonMapper = competitionJsonMapper;
    }

    @Transactional
    public int sync(JsonNode root) {
        List<Competition> competitions = competitionJsonMapper.fromRoot(root);
        Set<String> manuallyReviewedIds = new HashSet<>();
        reviewCandidateRepository.findAll().forEach(candidate -> {
            String status = candidate.getReviewStatus();
            if ("APPROVED".equals(status) || "REJECTED".equals(status)) {
                manuallyReviewedIds.add(candidate.getId());
            }
        });

        List<Competition> automaticUpdates = competitions.stream()
                .filter(item -> !manuallyReviewedIds.contains(item.getId()))
                .toList();

        competitionRepository.saveAll(automaticUpdates);
        competitionRepository.flush();
        return automaticUpdates.size();
    }
}
