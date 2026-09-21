package cn.trunghuy.competition;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.forwardedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

@SpringBootTest
@AutoConfigureMockMvc
class AdminSecurityTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void adminPageRedirectsToLoginWhenAnonymous() throws Exception {
        mockMvc.perform(get("/admin/"))
                .andExpect(status().is3xxRedirection())
                .andExpect(redirectedUrl("/admin/login.html"));
    }

    @Test
    void authenticatedAdminCanOpenReviewWorkspace() throws Exception {
        mockMvc.perform(
                        get("/admin/")
                                .with(user("admin").roles("ADMIN"))
                )
                .andExpect(status().isOk())
                .andExpect(forwardedUrl("/admin/index.html"));
    }

    @Test
    void publicCompetitionApiRemainsPublic() throws Exception {
        mockMvc.perform(get("/api/competitions"))
                .andExpect(status().isOk());
    }

    @Test
    void adminSessionRequiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/admin/session"))
                .andExpect(status().is3xxRedirection());
    }

    @Test
    void authenticatedAdminCanReadSessionAndReceivesCsrfToken() throws Exception {
        mockMvc.perform(
                        get("/api/admin/session")
                                .with(user("admin").roles("ADMIN"))
                )
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("admin"))
                .andExpect(jsonPath("$.csrf_token").isNotEmpty())
                .andExpect(jsonPath("$.csrf_header").isNotEmpty());
    }

    @Test
    void stateChangingAdminRequestRequiresCsrf() throws Exception {
        mockMvc.perform(
                        post("/api/admin/reviews/missing/reject")
                                .with(user("admin").roles("ADMIN"))
                                .contentType("application/json")
                                .content("{\"note\":\"test\"}")
                )
                .andExpect(status().isForbidden());
    }

    @Test
    void csrfProtectedAdminRequestReachesController() throws Exception {
        mockMvc.perform(
                        post("/api/admin/reviews/missing/reject")
                                .with(user("admin").roles("ADMIN"))
                                .with(csrf())
                                .contentType("application/json")
                                .content("{\"note\":\"test\"}")
                )
                .andExpect(status().isNotFound());
    }

    @Test
    void internalSyncUsesItsOwnTokenAndDoesNotRequireBrowserCsrf() throws Exception {
        mockMvc.perform(
                        post("/api/internal/sync")
                                .header("X-Sync-Token", "test-sync-token")
                                .contentType("application/json")
                                .content("{\"competitions\":[]}")
                )
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }
}
