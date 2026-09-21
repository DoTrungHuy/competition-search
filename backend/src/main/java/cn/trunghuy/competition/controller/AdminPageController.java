package cn.trunghuy.competition.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class AdminPageController {

    @GetMapping("/admin")
    public String adminRoot() {
        return "redirect:/admin/";
    }

    @GetMapping("/admin/")
    public String adminWorkspace() {
        return "forward:/admin/index.html";
    }
}
