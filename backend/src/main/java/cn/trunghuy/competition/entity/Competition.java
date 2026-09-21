package cn.trunghuy.competition.entity;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "competitions")
@Getter
@Setter
@NoArgsConstructor
public class Competition {

    @Id
    @Column(length = 120)
    private String id;

    @Column(name = "display_order", nullable = false)
    private int displayOrder;

    @Column(name = "brand_id", length = 120)
    private String brandId;

    @Column(nullable = false, length = 300)
    private String name;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "competition_categories", joinColumns = @JoinColumn(name = "competition_id"))
    @OrderColumn(name = "item_order")
    @Column(name = "category", length = 120)
    private List<String> category = new ArrayList<>();

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "competition_tags", joinColumns = @JoinColumn(name = "competition_id"))
    @OrderColumn(name = "item_order")
    @Column(name = "tag", length = 120)
    private List<String> tags = new ArrayList<>();

    @Column(length = 80)
    private String level;

    @Column(length = 80)
    private String kind;

    @Column(name = "info_channel", length = 120)
    private String infoChannel;

    @Column(length = 300)
    private String organizer;

    @Column(length = 1000)
    private String link;

    @Lob
    private String description;

    @Lob
    private String eligibility;

    @Column(name = "has_campus_notice")
    private Boolean hasCampusNotice;

    private Boolean active;

    @Column(length = 80)
    private String edition;

    @Column(name = "track_id", length = 160)
    private String trackId;

    @Column(name = "published_at")
    private LocalDate publishedAt;

    @Column(name = "registration_start")
    private LocalDate registrationStart;

    @Column(name = "registration_end")
    private LocalDate registrationEnd;

    @Column(name = "competition_start")
    private LocalDate competitionStart;

    @Column(name = "competition_end")
    private LocalDate competitionEnd;

    @Column(name = "last_checked")
    private LocalDate lastChecked;

    @Column(name = "needs_review")
    private Boolean needsReview;

    @Column(name = "status_override", length = 80)
    private String statusOverride;

    @Column(name = "schedule_source", length = 80)
    private String scheduleSource;

    @Column(name = "schedule_confidence", length = 80)
    private String scheduleConfidence;

    @Column(name = "link_kind", length = 80)
    private String linkKind;

    @Column(name = "registration_start_estimated")
    private LocalDate registrationStartEstimated;

    @Column(name = "registration_end_estimated")
    private LocalDate registrationEndEstimated;
}
