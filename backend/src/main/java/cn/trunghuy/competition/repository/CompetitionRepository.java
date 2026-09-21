package cn.trunghuy.competition.repository;

import cn.trunghuy.competition.entity.Competition;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CompetitionRepository extends JpaRepository<Competition, String> {

    List<Competition> findAllByOrderByDisplayOrderAsc();
}
