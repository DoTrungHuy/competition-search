package cn.trunghuy.competition.controller;

import cn.trunghuy.competition.entity.Competition;
import cn.trunghuy.competition.service.CompetitionService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/competitions")
public class CompetitionController {

    private final CompetitionService competitionService;

    public CompetitionController(CompetitionService competitionService) {
        this.competitionService = competitionService;
    }

    @GetMapping
    public List<Competition> getCompetitions(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String kind,
            @RequestParam(required = false) String level
    ) {
        return competitionService.findAll(keyword, kind, level);
    }

    @GetMapping("/{id}")
    public Competition getCompetition(@PathVariable String id) {
        return competitionService.findById(id);
    }
}
