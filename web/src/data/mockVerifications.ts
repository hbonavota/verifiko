import type { VerificationSummary } from "../types/verification";

export const mockVerifications: VerificationSummary[] = [
  {
    id: "vfk-2418",
    subject: "verifiko.es/login",
    normalizedInput: "https://verifiko.es/login",
    score: 36,
    riskLevel: "HIGH",
    verdict: "Likely malicious",
    status: "COMPLETED",
    createdAt: "2026-03-15T09:30:00Z",
    analystNote: "Escalate for credential collection review.",
    summary:
      "Visual impersonation and credential-lure language create a high-confidence phishing profile.",
    signals: [
      {
        id: "sig-1",
        title: "Brand impersonation",
        description: "Brand styling closely matches the legitimate destination.",
        reason:
          "Visual overlap with the legitimate service raises the likelihood that users will treat the page as trustworthy and submit credentials.",
        category: "Content behavior",
        severity: "HIGH",
        confidence: 92,
        source: "content-analyzer",
        scoreContribution: 18,
        status: "Escalated",
        evidence: ["Brand colors, typography, and login layout overlap with the legitimate service."],
      },
      {
        id: "sig-2",
        title: "Phishing keywords",
        description: "Credential-lure phrases appear in headline and form labels.",
        reason:
          "The wording is optimized for re-entry of credentials and account recovery urgency rather than neutral sign-in guidance.",
        category: "Content behavior",
        severity: "MEDIUM",
        confidence: 85,
        source: "nlp-analyzer",
        scoreContribution: 11,
        status: "Observed",
        evidence: ["Urgency and account access prompts are present in form labels and CTA copy."],
      },
    ],
    evidenceSummary: {
      observed: [
        "Visual design strongly resembles the brand being impersonated.",
        "Credential-oriented prompts are concentrated near the primary call to action.",
      ],
      sources: ["content-analyzer", "nlp-analyzer"],
      supportingContext: [
        "Normalized input resolved to a login path that mirrors the legitimate service structure.",
        "Content analysis and language analysis agreed on a credential collection profile without contradiction.",
      ],
      unresolved: ["Hosting history and passive DNS context have not been attached yet."],
    },
    executiveSummary: {
      posture:
        "The verification is operating in a high-risk posture because visual impersonation and credential-lure language both point toward phishing intent.",
      operationalImpact:
        "This result is strong enough to justify immediate analyst escalation, but infrastructure evidence should still be attached before a final containment record is issued.",
    },
    inconclusive: [
      {
        id: "inc-2418-1",
        title: "Infrastructure history is incomplete",
        detail:
          "Current scoring does not yet include passive DNS movement, registrar history, or hosting overlap with prior cases.",
        nextEvidence:
          "Attach passive DNS, registrar, and certificate lineage to determine whether the target belongs to a broader phishing cluster.",
      },
    ],
    recommendation: {
      title: "Open phishing case and prepare containment review",
      detail:
        "Escalate the verification into case handling, preserve the current evidence package, and add infrastructure context before recommending a block decision.",
      priority: "High priority",
      owner: "Verification response queue",
    },
    decisionTrace: [
      {
        id: "trace-2418-1",
        label: "Normalized input",
        detail:
          "Input normalized to https://verifiko.es/login with host, path, and form context retained for downstream analyzers.",
        outcome: "Canonical verification object created",
        timestamp: "2026-03-15T09:30:03Z",
      },
      {
        id: "trace-2418-2",
        label: "Collected content signals",
        detail:
          "Visual impersonation and credential-oriented language were both retained after analyzer agreement checks.",
        outcome: "2 material content signals attached",
        timestamp: "2026-03-15T09:30:10Z",
      },
      {
        id: "trace-2418-3",
        label: "Applied category penalties",
        detail:
          "Content behavior penalties dominated because both signals directly support a credential collection scenario.",
        outcome: "Score movement concentrated in content behavior",
        timestamp: "2026-03-15T09:30:14Z",
      },
      {
        id: "trace-2418-4",
        label: "Generated verdict summary",
        detail:
          "The score and explanation summary were produced without contradicting evidence strong enough to suppress the phishing interpretation.",
        outcome: "Verdict set to Likely malicious",
        timestamp: "2026-03-15T09:30:18Z",
      },
    ],
  },
  {
    id: "vfk-2421",
    subject: "payroll-gateway.net",
    normalizedInput: "https://payroll-gateway.net/",
    score: 58,
    riskLevel: "MEDIUM",
    verdict: "Suspicious",
    status: "COMPLETED",
    createdAt: "2026-03-14T16:05:00Z",
    analystNote: "Await passive DNS context before final disposition.",
    summary:
      "Suspicious redirect behavior is present, but evidence remains mixed without broader infrastructure context.",
    signals: [
      {
        id: "sig-3",
        title: "Suspicious redirect chain",
        description: "Target redirects across multiple unrelated domains before landing.",
        reason:
          "Multi-hop redirection weakens destination integrity and obscures what the analyst or end user actually reaches.",
        category: "Navigation behavior",
        severity: "MEDIUM",
        confidence: 78,
        source: "redirect-resolver",
        scoreContribution: 11,
        status: "Correlated",
        evidence: ["Observed redirects move across unrelated hostnames before final render."],
      },
      {
        id: "sig-5",
        title: "Credential lure language",
        description: "Recovery and account validation phrasing is optimized for rapid submission.",
        reason:
          "Account validation prompts and recovery framing increase the probability that the target is attempting credential collection rather than routine navigation.",
        category: "Content behavior",
        severity: "MEDIUM",
        confidence: 81,
        source: "nlp-analyzer",
        scoreContribution: 18,
        status: "Observed",
        evidence: ["Headline and form labels prioritize account revalidation language."],
      },
      {
        id: "sig-6",
        title: "Misleading subdomain",
        description: "The visible hostname structure suggests a trusted payroll context without matching ownership.",
        reason:
          "Payroll-oriented hostname wording implies internal trust, but the current ownership evidence does not support that framing.",
        category: "Domain structure",
        severity: "HIGH",
        confidence: 74,
        source: "url-normalizer",
        scoreContribution: 21,
        status: "Escalated",
        evidence: ["Subdomain wording implies internal payroll access while registration data does not align."],
      },
    ],
    evidenceSummary: {
      observed: [
        "Host structure suggests an internal payroll destination without matching ownership evidence.",
        "Credential-lure wording and redirect behavior both reinforce suspicion.",
      ],
      sources: ["redirect-resolver", "nlp-analyzer", "url-normalizer"],
      supportingContext: [
        "URL normalization preserved the payroll framing in the hostname and root path.",
        "Redirect resolution recorded intermediate hosts before the final rendered destination.",
        "Current dataset does not show confirmed overlap with a known malicious infrastructure cluster.",
      ],
      unresolved: [
        "Registrar history and passive DNS movement are still pending analyst review.",
        "No confirmed infrastructure overlap with known malicious clusters yet.",
      ],
    },
    executiveSummary: {
      posture:
        "The target currently sits in a medium-risk posture because domain framing, content cues, and redirect behavior collectively indicate suspicious intent.",
      operationalImpact:
        "The result is strong enough for case assignment and deeper review, but infrastructure context is still needed before a final containment or block recommendation can be justified.",
    },
    inconclusive: [
      {
        id: "inc-2421-1",
        title: "Infrastructure lineage is still pending",
        detail:
          "Registrar history, hosting shifts, and passive DNS movement have not yet been attached to the verification record.",
        nextEvidence:
          "Attach passive DNS and hosting history to determine whether the target is transient infrastructure or part of a durable pattern.",
      },
      {
        id: "inc-2421-2",
        title: "Cluster overlap remains unconfirmed",
        detail:
          "The observed signals are suspicious, but the current record does not connect the domain to a known campaign or infrastructure family.",
        nextEvidence:
          "Correlate name servers, certificate reuse, and historic resolutions against existing case data before final disposition.",
      },
    ],
    recommendation: {
      title: "Escalate for infrastructure validation",
      detail:
        "Assign the verification to an analyst case, preserve the current signal package, and attach passive DNS and certificate context before recommending containment.",
      priority: "Priority review",
      owner: "Threat review queue",
    },
    decisionTrace: [
      {
        id: "trace-2421-1",
        label: "Normalized input",
        detail:
          "Input normalized to https://payroll-gateway.net/ with canonical host and root path retained for comparison.",
        outcome: "Stable verification object created",
        timestamp: "2026-03-14T16:05:02Z",
      },
      {
        id: "trace-2421-2",
        label: "Collected signals",
        detail:
          "Redirect behavior, hostname framing, and credential-lure language all crossed retention thresholds.",
        outcome: "3 material signals attached to the record",
        timestamp: "2026-03-14T16:05:10Z",
      },
      {
        id: "trace-2421-3",
        label: "Applied category penalties",
        detail:
          "Domain structure contributed the largest score movement, with content behavior and redirect behavior adding secondary pressure.",
        outcome: "Category penalties raised overall concern",
        timestamp: "2026-03-14T16:05:13Z",
      },
      {
        id: "trace-2421-4",
        label: "Evaluated confidence limits",
        detail:
          "Infrastructure evidence remained incomplete, preventing a higher-confidence malicious disposition despite persistent suspicious signals.",
        outcome: "Confidence constrained by unresolved infrastructure context",
        timestamp: "2026-03-14T16:05:16Z",
      },
      {
        id: "trace-2421-5",
        label: "Generated explanation summary",
        detail:
          "The verification record was finalized with a readable explanation, unresolved evidence notes, and an analyst next-step recommendation.",
        outcome: "Verdict set to Suspicious with escalation guidance",
        timestamp: "2026-03-14T16:05:20Z",
      },
    ],
  },
  {
    id: "vfk-2424",
    subject: "portal-archive.gov.example",
    normalizedInput: "https://portal-archive.gov.example/",
    score: 84,
    riskLevel: "LOW",
    verdict: "Caution",
    status: "COMPLETED",
    createdAt: "2026-03-14T11:15:00Z",
    analystNote: "Monitor only. Current evidence does not justify blocking.",
    summary:
      "Minor structural anomalies were detected, but current evidence does not indicate active abuse.",
    signals: [
      {
        id: "sig-4",
        title: "Recent domain registration",
        description: "The registered domain is newer than the expected institution pattern.",
        reason:
          "Registration age introduces mild concern, but no strong corroborating evidence currently suggests active abuse.",
        category: "Domain reputation",
        severity: "LOW",
        confidence: 63,
        source: "dns-enricher",
        scoreContribution: 6,
        status: "Pending review",
        evidence: ["Registration age is lower than expected for an institutional archive domain."],
      },
    ],
    evidenceSummary: {
      observed: ["Registration age is lower than expected for an archive-style property."],
      sources: ["dns-enricher"],
      supportingContext: [
        "Current content review has not surfaced impersonation, credential-lure, or redirect anomalies.",
      ],
      unresolved: ["Content similarity and infrastructure history remain unverified."],
    },
    executiveSummary: {
      posture:
        "The target remains in a low-risk posture because only a minor registration anomaly is currently present.",
      operationalImpact:
        "The result supports monitoring rather than escalation. Additional evidence would improve confidence, but current indicators do not justify containment.",
    },
    inconclusive: [
      {
        id: "inc-2424-1",
        title: "Content review is incomplete",
        detail:
          "Current evidence does not yet include broader similarity checks or infrastructure history, leaving some uncertainty around institutional legitimacy.",
        nextEvidence:
          "Add content comparison and hosting history before converting the current caution posture into a firmer safe determination.",
      },
    ],
    recommendation: {
      title: "Monitor only",
      detail:
        "Preserve the low-risk record, avoid escalation, and revisit only if supporting content or infrastructure evidence changes the current posture.",
      priority: "Advisory",
      owner: "Monitoring queue",
    },
    decisionTrace: [
      {
        id: "trace-2424-1",
        label: "Normalized input",
        detail:
          "Institution-style hostname normalized for age and content review without loss of host structure.",
        outcome: "Verification object created",
        timestamp: "2026-03-14T11:15:03Z",
      },
      {
        id: "trace-2424-2",
        label: "Collected registration evidence",
        detail:
          "DNS enrichment returned a younger registration age than expected for an archive-oriented institutional property.",
        outcome: "Single low-severity signal retained",
        timestamp: "2026-03-14T11:15:08Z",
      },
      {
        id: "trace-2424-3",
        label: "Calculated score",
        detail:
          "No compounding content or redirect penalties were present, so the score remained in a low-risk range.",
        outcome: "Verdict set to Caution",
        timestamp: "2026-03-14T11:15:13Z",
      },
    ],
  },
];
