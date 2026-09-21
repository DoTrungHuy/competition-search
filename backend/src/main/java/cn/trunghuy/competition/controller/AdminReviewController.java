package cn.trunghuy.competition.controller;

import cn.trunghuy.competition.dto.ReviewActionRequest;
import cn.trunghuy.competition.dto.ReviewCandidateResponse;
import cn.trunghuy.competition.service.AdminReviewService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@RestController
@RequestMapping("/api/admin/reviews")
public class AdminReviewController {

    private final AdminReviewService adminReviewService;

    public AdminReviewController(AdminReviewService adminReviewService) {
        this.adminReviewService = adminReviewService;
    }

    @GetMapping
    public List<ReviewCandidateResponse> list(
            @RequestParam(required = false) String status
    ) {
        return adminReviewService.findAll(status);
    }

    @GetMapping("/{id}")
    public ReviewCandidateResponse detail(
            @PathVariable String id
    ) {
        return adminReviewService.findById(id);
    }

    @PostMapping("/{id}/approve")
    public ReviewCandidateResponse approve(
            @PathVariable String id,
            @RequestBody(required = false) ReviewActionRequest request
    ) {
        return adminReviewService.approve(
                id,
                request == null ? null : request.note(),
                request == null ? null : request.data()
        );
    }

    @PostMapping("/{id}/reject")
    public ReviewCandidateResponse reject(
            @PathVariable String id,
            @RequestBody(required = false) ReviewActionRequest request
    ) {
        return adminReviewService.reject(id, request == null ? null : request.note());
    }
}
