package cn.trunghuy.competition.service;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.repository.CompetitionRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Locale;

@Service
public class CompetitionService {

    private final CompetitionRepository competitionRepository;

    public CompetitionService(CompetitionRepository competitionRepository) {
        this.competitionRepository = competitionRepository;
    }

    public List<Competition> findAll(String keyword, String kind, String level) {
        String normalizedKeyword = normalize(keyword);
        String normalizedKind = normalize(kind);
        String normalizedLevel = normalize(level);

        return competitionRepository.findAllByOrderByDisplayOrderAsc().stream()
                .filter(item -> normalizedKind.isEmpty() || normalize(item.getKind()).equals(normalizedKind))
                .filter(item -> normalizedLevel.isEmpty() || normalize(item.getLevel()).equals(normalizedLevel))
                .filter(item -> normalizedKeyword.isEmpty() || matchesKeyword(item, normalizedKeyword))
                .toList();
    }

    public Competition findById(String id) {
        return competitionRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Competition not found: " + id
                ));
    }

    private boolean matchesKeyword(Competition item, String keyword) {
        if (normalize(item.getName()).contains(keyword)) return true;
        if (normalize(item.getDescription()).contains(keyword)) return true;
        if (normalize(item.getOrganizer()).contains(keyword)) return true;
        return item.getCategory().stream().anyMatch(value -> normalize(value).contains(keyword))
                || item.getTags().stream().anyMatch(value -> normalize(value).contains(keyword));
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }
}
