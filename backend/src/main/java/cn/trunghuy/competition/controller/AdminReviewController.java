package cn.trunghuy.competition.controller;

import cn.trunghuy.competition.dto.ReviewActionRequest;
import cn.trunghuy.competition.dto.ReviewCandidateResponse;
import cn.trunghuy.competition.service.AdminReviewService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

@RestController
@RequestMapping("/api/admin/reviews")
public class AdminReviewController {

    private final AdminReviewService adminReviewService;
    private final String adminToken;

    public AdminReviewController(
            AdminReviewService adminReviewService,
            @Value("${competition.admin-token:}") String adminToken
    ) {
        this.adminReviewService = adminReviewService;
        this.adminToken = adminToken;
    }

    @GetMapping
    public List<ReviewCandidateResponse> list(
            @RequestHeader(value = "X-Admin-Token", required = false) String token,
            @RequestParam(required = false) String status
    ) {
        requireAdmin(token);
        return adminReviewService.findAll(status);
    }

    @GetMapping("/{id}")
    public ReviewCandidateResponse detail(
            @RequestHeader(value = "X-Admin-Token", required = false) String token,
            @PathVariable String id
    ) {
        requireAdmin(token);
        return adminReviewService.findById(id);
    }

    @PostMapping("/{id}/approve")
    public ReviewCandidateResponse approve(
            @RequestHeader(value = "X-Admin-Token", required = false) String token,
            @PathVariable String id,
            @RequestBody(required = false) ReviewActionRequest request
    ) {
        requireAdmin(token);
        return adminReviewService.approve(id, request == null ? null : request.note());
    }

    @PostMapping("/{id}/reject")
    public ReviewCandidateResponse reject(
            @RequestHeader(value = "X-Admin-Token", required = false) String token,
            @PathVariable String id,
            @RequestBody(required = false) ReviewActionRequest request
    ) {
        requireAdmin(token);
        return adminReviewService.reject(id, request == null ? null : request.note());
    }

    private void requireAdmin(String suppliedToken) {
        if (adminToken.isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Admin token is not configured"
            );
        }
        if (suppliedToken == null || !MessageDigest.isEqual(
                adminToken.getBytes(StandardCharsets.UTF_8),
                suppliedToken.getBytes(StandardCharsets.UTF_8)
        )) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Invalid admin token");
        }
    }
}
