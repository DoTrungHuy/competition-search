package cn.trunghuy.competition.controller;

import cn.trunghuy.competition.service.CompetitionSyncService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Map;

@RestController
@RequestMapping("/api/internal")
public class InternalSyncController {

    private final CompetitionSyncService competitionSyncService;
    private final String syncToken;

    public InternalSyncController(
            CompetitionSyncService competitionSyncService,
            @Value("${competition.sync-token:}") String syncToken
    ) {
        this.competitionSyncService = competitionSyncService;
        this.syncToken = syncToken;
    }

    @PostMapping("/sync")
    @ResponseStatus(HttpStatus.OK)
    public Map<String, Object> sync(
            @RequestHeader(value = "X-Sync-Token", required = false) String suppliedToken,
            @RequestBody JsonNode body
    ) {
        if (syncToken.isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Sync token is not configured"
            );
        }
        if (!tokenMatches(syncToken, suppliedToken)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Invalid sync token");
        }

        JsonNode competitions = body.path("competitions");
        if (!competitions.isArray()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "competitions must be an array"
            );
        }

        int synced = competitionSyncService.replaceAll(body);
        return Map.of(
                "status", "ok",
                "synced", synced
        );
    }

    private boolean tokenMatches(String expected, String supplied) {
        if (supplied == null) {
            return false;
        }
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                supplied.getBytes(StandardCharsets.UTF_8)
        );
    }
}
