package cn.trunghuy.competition.controller;

import org.springframework.security.core.Authentication;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class AdminSessionController {

    @GetMapping("/csrf")
    public Map<String, String> csrf(CsrfToken csrfToken) {
        return Map.of(
                "token", csrfToken.getToken(),
                "header_name", csrfToken.getHeaderName(),
                "parameter_name", csrfToken.getParameterName()
        );
    }

    @GetMapping("/admin/session")
    public Map<String, String> session(Authentication authentication, CsrfToken csrfToken) {
        return Map.of(
                "username", authentication.getName(),
                "csrf_token", csrfToken.getToken(),
                "csrf_header", csrfToken.getHeaderName()
        );
    }
}
