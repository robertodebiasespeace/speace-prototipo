"""
SPEACE Neural Engine - Environment Sensor
Sensore ambiente esterno: Natura, società umana, tecnologie, governi, leggi.
"""

from __future__ import annotations

import uuid
import time
import json
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable
from collections import defaultdict

import requests


class EnvironmentDomain(Enum):
    NATURE = auto()
    HUMAN_SOCIETY = auto()
    TECHNOLOGY = auto()
    GOVERNANCE = auto()
    LAW = auto()
    ECONOMY = auto()
    CULTURE = auto()
    HEALTH = auto()
    EDUCATION = auto()


class ImpactDirection(Enum):
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()
    UNKNOWN = auto()


@dataclass
class EnvironmentalFactor:
    factor_id: str
    domain: EnvironmentDomain
    name: str
    description: str
    value: float
    trend: float
    impact_score: float
    last_updated: float = field(default_factory=time.time)
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Constraint:
    constraint_id: str
    domain: EnvironmentDomain
    type: str
    description: str
    severity: float
    applicable: bool = True
    source: str = ""
    legal_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Opportunity:
    opportunity_id: str
    domain: EnvironmentDomain
    type: str
    description: str
    potential_impact: float
    feasibility: float
    timeframe: str = "medium"
    resources_required: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentalReport:
    report_id: str
    timestamp: float
    domain_reports: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Constraint] = field(default_factory=list)
    opportunities: List[Opportunity] = field(default_factory=list)
    overall_impact: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class NatureSensor:
    def __init__(self):
        self._factors: Dict[str, EnvironmentalFactor] = {}
        self._update_interval = 3600
        self._last_comprehensive_update = 0

    def update_factors(self) -> Dict[str, EnvironmentalFactor]:
        self._factors["carbon_footprint"] = EnvironmentalFactor(
            factor_id="carbon_footprint",
            domain=EnvironmentDomain.NATURE,
            name="Carbon Footprint",
            description="Carbon emissions impact",
            value=0.5,
            trend=-0.02,
            impact_score=-0.3,
            source="internal"
        )

        self._factors["biodiversity_index"] = EnvironmentalFactor(
            factor_id="biodiversity_index",
            domain=EnvironmentDomain.NATURE,
            name="Biodiversity Index",
            description="Measure of ecosystem diversity",
            value=0.65,
            trend=0.01,
            impact_score=0.4,
            source="internal"
        )

        self._factors["resource_availability"] = EnvironmentalFactor(
            factor_id="resource_availability",
            domain=EnvironmentDomain.NATURE,
            name="Resource Availability",
            description="Natural resource availability",
            value=0.7,
            trend=-0.01,
            impact_score=0.3,
            source="internal"
        )

        self._factors["climate_stability"] = EnvironmentalFactor(
            factor_id="climate_stability",
            domain=EnvironmentDomain.NATURE,
            name="Climate Stability",
            description="Global climate stability index",
            value=0.4,
            trend=-0.005,
            impact_score=-0.5,
            source="external"
        )

        return self._factors

    def get_constraints(self) -> List[Constraint]:
        return [
            Constraint(
                constraint_id="env_regulation_1",
                domain=EnvironmentDomain.NATURE,
                type="emission_limit",
                description="Environmental emission regulations",
                severity=0.7,
                source="EU Environmental Directives",
                legal_reference="EU 2021/1119"
            )
        ]

    def get_opportunities(self) -> List[Opportunity]:
        return [
            Opportunity(
                opportunity_id="eco_tech",
                domain=EnvironmentDomain.NATURE,
                type="green_technology",
                description="Green technology integration",
                potential_impact=0.6,
                feasibility=0.7,
                timeframe="medium"
            )
        ]


class HumanSocietySensor:
    def __init__(self):
        self._factors: Dict[str, EnvironmentalFactor] = {}

    def update_factors(self) -> Dict[str, EnvironmentalFactor]:
        self._factors["social_cohesion"] = EnvironmentalFactor(
            factor_id="social_cohesion",
            domain=EnvironmentDomain.HUMAN_SOCIETY,
            name="Social Cohesion",
            description="Measure of social stability and cohesion",
            value=0.55,
            trend=0.005,
            impact_score=0.4,
            source="internal"
        )

        self._factors["wellbeing_index"] = EnvironmentalFactor(
            factor_id="wellbeing_index",
            domain=EnvironmentDomain.HUMAN_SOCIETY,
            name="Global Wellbeing Index",
            description="Human wellbeing and quality of life",
            value=0.6,
            trend=0.008,
            impact_score=0.5,
            source="external"
        )

        self._factors["population_stability"] = EnvironmentalFactor(
            factor_id="population_stability",
            domain=EnvironmentDomain.HUMAN_SOCIETY,
            name="Population Stability",
            description="Population growth rate and stability",
            value=0.5,
            trend=-0.002,
            impact_score=0.2,
            source="external"
        )

        return self._factors

    def get_constraints(self) -> List[Constraint]:
        return [
            Constraint(
                constraint_id="social_norm_1",
                domain=EnvironmentDomain.HUMAN_SOCIETY,
                type="privacy_norm",
                description="Social norms around data privacy",
                severity=0.6,
                source="GDPR cultural adaptation"
            )
        ]

    def get_opportunities(self) -> List[Opportunity]:
        return [
            Opportunity(
                opportunity_id="collaboration_platform",
                domain=EnvironmentDomain.HUMAN_SOCIETY,
                type="social_platform",
                description="Digital collaboration platforms",
                potential_impact=0.55,
                feasibility=0.8,
                timeframe="short"
            )
        ]


class TechnologySensor:
    def __init__(self):
        self._factors: Dict[str, EnvironmentalFactor] = {}

    def update_factors(self) -> Dict[str, EnvironmentalFactor]:
        self._factors["ai_maturity"] = EnvironmentalFactor(
            factor_id="ai_maturity",
            domain=EnvironmentDomain.TECHNOLOGY,
            name="AI Technology Maturity",
            description="Maturity level of AI technologies",
            value=0.7,
            trend=0.02,
            impact_score=0.6,
            source="internal"
        )

        self._factors["infrastructure_readiness"] = EnvironmentalFactor(
            factor_id="infrastructure_readiness",
            domain=EnvironmentDomain.TECHNOLOGY,
            name="Digital Infrastructure Readiness",
            description="Readiness of digital infrastructure",
            value=0.65,
            trend=0.015,
            impact_score=0.5,
            source="external"
        )

        self._factors["connectivity_index"] = EnvironmentalFactor(
            factor_id="connectivity_index",
            domain=EnvironmentDomain.TECHNOLOGY,
            name="Global Connectivity",
            description="Internet and connectivity coverage",
            value=0.75,
            trend=0.01,
            impact_score=0.4,
            source="external"
        )

        return self._factors

    def get_constraints(self) -> List[Constraint]:
        return [
            Constraint(
                constraint_id="tech_standard_1",
                domain=EnvironmentDomain.TECHNOLOGY,
                type="interoperability_standard",
                description="Technology interoperability requirements",
                severity=0.5,
                source="ISO/IEC standards"
            )
        ]

    def get_opportunities(self) -> List[Opportunity]:
        return [
            Opportunity(
                opportunity_id="ai_integration",
                domain=EnvironmentDomain.TECHNOLOGY,
                type="ai_advancement",
                description="Advanced AI integration opportunities",
                potential_impact=0.8,
                feasibility=0.6,
                timeframe="long"
            )
        ]


class GovernanceSensor:
    def __init__(self):
        self._factors: Dict[str, EnvironmentalFactor] = {}

    def update_factors(self) -> Dict[str, EnvironmentalFactor]:
        self._factors["governance_effectiveness"] = EnvironmentalFactor(
            factor_id="governance_effectiveness",
            domain=EnvironmentDomain.GOVERNANCE,
            name="Governance Effectiveness",
            description="Effectiveness of global governance",
            value=0.45,
            trend=0.005,
            impact_score=0.3,
            source="internal"
        )

        self._factors["policy_alignment"] = EnvironmentalFactor(
            factor_id="policy_alignment",
            domain=EnvironmentDomain.GOVERNANCE,
            name="Policy Alignment",
            description="Alignment with international policies",
            value=0.55,
            trend=0.008,
            impact_score=0.4,
            source="internal"
        )

        return self._factors

    def get_constraints(self) -> List[Constraint]:
        return [
            Constraint(
                constraint_id="govt_regulation_1",
                domain=EnvironmentDomain.GOVERNANCE,
                type="ai_regulation",
                description="AI governance and regulation frameworks",
                severity=0.8,
                source="EU AI Act",
                legal_reference="EU AI Act 2024"
            )
        ]

    def get_opportunities(self) -> List[Opportunity]:
        return [
            Opportunity(
                opportunity_id="policy_influence",
                domain=EnvironmentDomain.GOVERNANCE,
                type="policy_development",
                description="Participate in policy development",
                potential_impact=0.5,
                feasibility=0.4,
                timeframe="long"
            )
        ]


class LawSensor:
    def __init__(self):
        self._factors: Dict[str, EnvironmentalFactor] = {}

    def update_factors(self) -> Dict[str, EnvironmentalFactor]:
        self._factors["legal_clarity"] = EnvironmentalFactor(
            factor_id="legal_clarity",
            domain=EnvironmentDomain.LAW,
            name="Legal Framework Clarity",
            description="Clarity of applicable legal frameworks",
            value=0.5,
            trend=0.01,
            impact_score=0.4,
            source="internal"
        )

        self._factors["compliance_burden"] = EnvironmentalFactor(
            factor_id="compliance_burden",
            domain=EnvironmentDomain.LAW,
            name="Compliance Burden",
            description="Regulatory compliance complexity",
            value=0.6,
            trend=-0.005,
            impact_score=-0.3,
            source="internal"
        )

        return self._factors

    def get_constraints(self) -> List[Constraint]:
        return [
            Constraint(
                constraint_id="legal_constraint_1",
                domain=EnvironmentDomain.LAW,
                type="constitutional_right",
                description="Constitutional rights protection",
                severity=0.9,
                source="Italian Constitution",
                legal_reference="Art. 2, 3, 41"
            ),
            Constraint(
                constraint_id="legal_constraint_2",
                domain=EnvironmentDomain.LAW,
                type="data_protection",
                description="Data protection requirements",
                severity=0.85,
                source="GDPR",
                legal_reference="EU 2016/679"
            ),
            Constraint(
                constraint_id="legal_constraint_3",
                domain=EnvironmentDomain.LAW,
                type="liability",
                description="Liability frameworks for AI",
                severity=0.7,
                source="EU AI Act",
                legal_reference="Chapter V"
            )
        ]

    def get_opportunities(self) -> List[Opportunity]:
        return []


class EnvironmentSensor:
    VERSION = "1.0.0"

    def __init__(self):
        self._sensors = {
            EnvironmentDomain.NATURE: NatureSensor(),
            EnvironmentDomain.HUMAN_SOCIETY: HumanSocietySensor(),
            EnvironmentDomain.TECHNOLOGY: TechnologySensor(),
            EnvironmentDomain.GOVERNANCE: GovernanceSensor(),
            EnvironmentDomain.LAW: LawSensor()
        }

        self._factors: Dict[str, EnvironmentalFactor] = {}
        self._constraints: Dict[str, Constraint] = {}
        self._opportunities: Dict[str, Opportunity] = {}

        self._lock = threading.RLock()
        self._callbacks: Dict[str, Callable] = {}
        self._last_full_scan = 0
        self._scan_interval = 1800

    def scan_environment(self) -> EnvironmentalReport:
        with self._lock:
            report_id = f"env_report_{uuid.uuid4().hex[:12]}"
            domain_reports = {}

            for domain, sensor in self._sensors.items():
                factors = sensor.update_factors()
                self._factors.update(factors)

                domain_reports[domain.name] = {
                    "factor_count": len(factors),
                    "factors": {
                        fid: {
                            "name": f.name,
                            "value": f.value,
                            "trend": f.trend,
                            "impact_score": f.impact_score
                        }
                        for fid, f in factors.items()
                    }
                }

            all_constraints = []
            all_opportunities = []

            for sensor in self._sensors.values():
                all_constraints.extend(sensor.get_constraints())
                all_opportunities.extend(sensor.get_opportunities())

            for c in all_constraints:
                self._constraints[c.constraint_id] = c

            for o in all_opportunities:
                self._opportunities[o.opportunity_id] = o

            overall_impact = self._calculate_overall_impact()

            recommendations = self._generate_recommendations(all_constraints, all_opportunities)

            report = EnvironmentalReport(
                report_id=report_id,
                timestamp=time.time(),
                domain_reports=domain_reports,
                constraints=all_constraints,
                opportunities=all_opportunities,
                overall_impact=overall_impact,
                recommendations=recommendations
            )

            self._last_full_scan = time.time()

            return report

    def _calculate_overall_impact(self) -> float:
        if not self._factors:
            return 0.0

        positive = sum(f.impact_score for f in self._factors.values() if f.impact_score > 0)
        negative = sum(f.impact_score for f in self._factors.values() if f.impact_score < 0)

        return (positive + negative) / len(self._factors)

    def _generate_recommendations(
        self,
        constraints: List[Constraint],
        opportunities: List[Opportunity]
    ) -> List[str]:
        recommendations = []

        high_severity = [c for c in constraints if c.severity > 0.7]
        if high_severity:
            recommendations.append(
                f"Address {len(high_severity)} high-severity environmental constraints"
            )

        high_impact = [o for o in opportunities if o.potential_impact > 0.7]
        if high_impact:
            recommendations.append(
                f"Explore {len(high_impact)} high-potential opportunities"
            )

        negative_impact_factors = [f for f in self._factors.values() if f.impact_score < -0.3]
        if negative_impact_factors:
            recommendations.append(
                f"Reduce negative impact from: {', '.join(f.name for f in negative_impact_factors)}"
            )

        return recommendations

    def get_active_constraints(self, domain: Optional[EnvironmentDomain] = None) -> List[Constraint]:
        if domain:
            return [c for c in self._constraints.values() if c.domain == domain and c.applicable]
        return [c for c in self._constraints.values() if c.applicable]

    def get_opportunities(
        self,
        domain: Optional[EnvironmentDomain] = None,
        min_impact: float = 0.0
    ) -> List[Opportunity]:
        results = []
        for o in self._opportunities.values():
            if domain and o.domain != domain:
                continue
            if o.potential_impact >= min_impact:
                results.append(o)

        return sorted(results, key=lambda x: x.potential_impact, reverse=True)

    def get_factor(self, factor_id: str) -> Optional[EnvironmentalFactor]:
        return self._factors.get(factor_id)

    def get_domain_summary(self, domain: EnvironmentDomain) -> Dict[str, Any]:
        domain_factors = {
            fid: f for fid, f in self._factors.items()
            if f.domain == domain
        }

        if not domain_factors:
            return {}

        avg_value = sum(f.value for f in domain_factors.values()) / len(domain_factors)
        avg_impact = sum(f.impact_score for f in domain_factors.values()) / len(domain_factors)
        trend = sum(f.trend for f in domain_factors.values()) / len(domain_factors)

        return {
            "domain": domain.name,
            "factor_count": len(domain_factors),
            "average_value": avg_value,
            "average_impact": avg_impact,
            "combined_trend": trend
        }

    def check_compliance(self, domain: EnvironmentDomain) -> Dict[str, Any]:
        constraints = self.get_active_constraints(domain)
        violated = []
        satisfied = []

        for c in constraints:
            if c.severity > 0.7:
                violated.append({
                    "constraint_id": c.constraint_id,
                    "description": c.description,
                    "severity": c.severity
                })
            else:
                satisfied.append(c.constraint_id)

        return {
            "domain": domain.name,
            "total_constraints": len(constraints),
            "violated_count": len(violated),
            "violated_constraints": violated,
            "satisfied_count": len(satisfied),
            "compliance_score": len(satisfied) / len(constraints) if constraints else 1.0
        }

    def get_environmental_context(self) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "factor_count": len(self._factors),
            "constraint_count": len(self._constraints),
            "opportunity_count": len(self._opportunities),
            "domains": {
                domain.name: self.get_domain_summary(domain)
                for domain in EnvironmentDomain
            },
            "overall_impact": self._calculate_overall_impact()
        }

    def register_callback(self, name: str, callback: Callable):
        self._callbacks[name] = callback

    def notify_change(self, factor_id: str, old_value: float, new_value: float):
        for callback in self._callbacks.values():
            try:
                callback(factor_id, old_value, new_value)
            except Exception:
                pass
