package cn.trunghuy.competition.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;

@Entity
@Table(name = "review_candidates")
@Getter
@Setter
@NoArgsConstructor
public class ReviewCandidate {

    @Id
    @Column(length = 180)
    private String id;

    @Column(nullable = false, length = 300)
    private String name;

    @Column(length = 1000)
    private String link;

    @Column(length = 120)
    private String source;

    @Column(name = "source_name", length = 200)
    private String sourceName;

    @Column(name = "ai_verdict", length = 40)
    private String aiVerdict;

    @Column(name = "ai_confidence", length = 40)
    private String aiConfidence;

    @Column(name = "ai_reason")
    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    private String aiReason;

    @Column(name = "review_status", nullable = false, length = 20)
    private String reviewStatus;

    @Column(name = "raw_data", nullable = false)
    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    private String rawData;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
