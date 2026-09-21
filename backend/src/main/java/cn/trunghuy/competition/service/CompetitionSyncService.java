package cn.trunghuy.competition.service;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.repository.CompetitionRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;

import java.util.List;

@Service
public class CompetitionSyncService {

    private final CompetitionRepository competitionRepository;
    private final CompetitionJsonMapper competitionJsonMapper;

    public CompetitionSyncService(
            CompetitionRepository competitionRepository,
            CompetitionJsonMapper competitionJsonMapper
    ) {
        this.competitionRepository = competitionRepository;
        this.competitionJsonMapper = competitionJsonMapper;
    }

    @Transactional
    public int replaceAll(JsonNode root) {
        List<Competition> competitions = competitionJsonMapper.fromRoot(root);
        competitionRepository.deleteAll();
        competitionRepository.flush();
        competitionRepository.saveAll(competitions);
        competitionRepository.flush();
        return competitions.size();
    }
}
