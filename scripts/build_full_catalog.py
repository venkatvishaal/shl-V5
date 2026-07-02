"""
build_full_catalog.py
---------------------
Builds the complete SHL assessment catalog from structured data.
Saves the result to data/catalog.json in the format the codebase expects.

Usage:
    python scripts/build_full_catalog.py
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Mapping from catalog "keys" to internal test_type codes
# -------------------------------------------------------------------
_KEY_TO_TYPE: Dict[str, str] = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "SI",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}


def parse_duration(duration_str: str) -> int | None:
    if not duration_str or str(duration_str).strip() in ("", "-", "N/A", "Variable", "Untimed", "TBC"):
        return None
    m = re.search(r"(\d+)", str(duration_str))
    if not m:
        return None
    val = int(m.group(1))
    lower = str(duration_str).lower()
    if "hour" in lower or "hr" in lower:
        val *= 60
    return val


def normalize_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    keys = item.get("keys", [])
    test_type = "U"
    for k in keys:
        mapped = _KEY_TO_TYPE.get(k)
        if mapped:
            test_type = mapped
            break
    return {
        "name": item.get("name", ""),
        "url": item.get("link", ""),
        "test_type": test_type,
        "description": item.get("description", ""),
        "dimensions": [],
        "duration_minutes": parse_duration(item.get("duration", "")),
        "target_levels": [lv.lower() for lv in item.get("job_levels", [])],
        "use_cases": [k.lower() for k in keys],
        "scraped_at": item.get("scraped_at", ""),
        "_original": {"entity_id": str(item.get("entity_id", ""))},
    }


def main():
    entries: List[Dict[str, Any]] = [
        {
            "entity_id": "4302",
            "name": "Global Skills Development Report",
            "link": "https://www.shl.com/products/product-catalog/view/global-skills-development-report/",
            "job_levels": ["Director","Entry-Level","Executive","General Population","Graduate","Manager","Mid-Professional","Front Line Manager","Supervisor"],
            "languages": [],
            "duration": "",
            "description": "This report is designed to be given to individuals who have completed the Global Skills Assessment (GSA). With coverage across the Great 8 Domains, this measure of self-reported behaviors offers a complete overview of their current skills. Participants receive actionable tips on leveraging their top skill strengths and how they might develop their growth skills.",
            "keys": ["Ability & Aptitude","Assessment Exercises","Biodata & Situational Judgment","Competencies","Development & 360","Personality & Behavior"],
            "scraped_at": "2026-05-08T10:40:21.464836+00:00"
        },
        {
            "entity_id": "3827",
            "name": ".NET Framework 4.5",
            "link": "https://www.shl.com/products/product-catalog/view/net-framework-4-5/",
            "job_levels": ["Professional Individual Contributor","Mid-Professional"],
            "languages": ["English (USA)"],
            "duration": "30 minutes",
            "description": "The.NET Framework 4.5 test measures knowledge of .NET environment. Designed for experienced users, this test covers the following topics: Application Development, Application Foundation, Data Modeling, Deployment, Diagnostics, Performance, Portability, and Security.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:39:46.810448+00:00"
        },
        {
            "entity_id": "4094",
            "name": ".NET MVC (New)",
            "link": "https://www.shl.com/products/product-catalog/view/net-mvc-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "17 minutes",
            "description": "Multi-choice test that measures the knowledge of Model-View-Controller (MVC) architecture, validation, security, routing, and areas.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:39:53.276083+00:00"
        },
        {
            "entity_id": "4099",
            "name": ".NET MVVM (New)",
            "link": "https://www.shl.com/products/product-catalog/view/net-mvvm-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "5 minutes",
            "description": "Multi-choice test that measures the knowledge of MVVM pattern, scenarios, data validation, ViewModel communication and Quick-start.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:41:53.047159+00:00"
        },
        {
            "entity_id": "4018",
            "name": ".NET WCF (New)",
            "link": "https://www.shl.com/products/product-catalog/view/net-wcf-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "11 minutes",
            "description": "Multi-choice test that measures the knowledge of .NET fundamentals, WCF architecture, programming model, SOA, managing and programming WCF.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:42:04.800928+00:00"
        },
        {
            "entity_id": "4016",
            "name": ".NET WPF (New)",
            "link": "https://www.shl.com/products/product-catalog/view/net-wpf-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of .NET basics, WPF, XAML controls, events, layouts, working with WPF windows/menus and deploying WPF applications.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:42:04.800928+00:00"
        },
        {
            "entity_id": "4165",
            "name": ".NET XAML (New)",
            "link": "https://www.shl.com/products/product-catalog/view/net-xaml-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "5 minutes",
            "description": "Multi-choice test that measures the knowledge of XAML triggers, data binding, custom controls and layouts.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:42:15.406285+00:00"
        },
        {
            "entity_id": "4178",
            "name": "Accounts Payable (New)",
            "link": "https://www.shl.com/products/product-catalog/view/accounts-payable-new/",
            "job_levels": ["Entry-Level","Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multiple-choice test that measures the knowledge of processing payables and vendor invoices, and the posting of journal entries.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:42:34.043781+00:00"
        },
        {
            "entity_id": "4187",
            "name": "Accounts Payable Simulation (New)",
            "link": "https://www.shl.com/products/product-catalog/view/accounts-payable-simulation-new/",
            "job_levels": ["Entry-Level","Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Simulated data entry test that measures the ability to process payables and vendor invoices.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:42:40.400062+00:00"
        },
        {
            "entity_id": "4179",
            "name": "Accounts Receivable (New)",
            "link": "https://www.shl.com/products/product-catalog/view/accounts-receivable-new/",
            "job_levels": ["Entry-Level","Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multiple-choice test that measures the knowledge of processing receivables and invoices.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:42:48.008104+00:00"
        },
        {
            "entity_id": "4188",
            "name": "Accounts Receivable Simulation (New)",
            "link": "https://www.shl.com/products/product-catalog/view/accounts-receivable-simulation-new/",
            "job_levels": ["Entry-Level","Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Simulated data entry test that measures the ability to process receivables and invoices.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:42:54.709323+00:00"
        },
        {
            "entity_id": "4168",
            "name": "ADO.NET (New)",
            "link": "https://www.shl.com/products/product-catalog/view/ado-net-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge on the concepts of ADO.NET architecture, components and data provider objects.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:00.681789+00:00"
        },
        {
            "entity_id": "4019",
            "name": "Adobe Experience Manager (New)",
            "link": "https://www.shl.com/products/product-catalog/view/adobe-experience-manager-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "17 minutes",
            "description": "Multi-choice test that measures the knowledge of AEM components, templates, workflows, AEM collections, OSGi services and troubleshooting of AEM projects.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:07.224360+00:00"
        },
        {
            "entity_id": "3778",
            "name": "Adobe Photoshop CC",
            "link": "https://www.shl.com/products/product-catalog/view/adobe-photoshop-cc/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "20 minutes",
            "description": "The Adobe Photoshop CC test measures knowledge of Adobe Photoshop CC. Designed for experienced users, this test covers the following topics: 3D, Color, File Management, Interface, Layers, Painting and Drawing, Retouch and Enhancements, Selection, Text, and Web.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:13.300957+00:00"
        },
        {
            "entity_id": "4069",
            "name": "Aeronautical Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/aeronautical-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of flight mechanics, space dynamics, aerodynamics, structures and propulsion.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:21.526635+00:00"
        },
        {
            "entity_id": "4004",
            "name": "Aerospace Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/aerospace-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of aerodynamics, aircraft systems and instrumentation, flight dynamics, space dynamics and avionics.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:27.704593+00:00"
        },
        {
            "entity_id": "4223",
            "name": "Agile Software Development",
            "link": "https://www.shl.com/products/product-catalog/view/agile-software-development/",
            "job_levels": ["Graduate"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the knowledge of agile methodology, scrum, feature driven software development, incremental and iterative development and processes involved in agile software development.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:35.218571+00:00"
        },
        {
            "entity_id": "4159",
            "name": "Agile Testing (New)",
            "link": "https://www.shl.com/products/product-catalog/view/agile-testing-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multi-choice test that measures the knowledge of tools, techniques and processes involved in the Agile testing methodology.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:41.269701+00:00"
        },
        {
            "entity_id": "4311",
            "name": "AI Skills",
            "link": "https://www.shl.com/products/product-catalog/view/ai-skills/",
            "job_levels": ["General Population"],
            "languages": ["English (USA)"],
            "duration": "16 minutes",
            "description": "The AI Skills assessment measures the skills that help candidates successfully leverage AI in their work.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:43:51.702137+00:00"
        },
        {
            "entity_id": "4028",
            "name": "Amazon Web Services (AWS) Development (New)",
            "link": "https://www.shl.com/products/product-catalog/view/amazon-web-services-aws-development-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "6 minutes",
            "description": "Multi-choice test that measures the knowledge of AWS delivery process, monitoring, metrics, logging, security, validation and scalability.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:43:58.111884+00:00"
        },
        {
            "entity_id": "4160",
            "name": "Android Development (New)",
            "link": "https://www.shl.com/products/product-catalog/view/android-development-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the knowledge of UI components for an Android device, services and alerts, animation and media apps, application components, security and testing.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:04.732109+00:00"
        },
        {
            "entity_id": "4153",
            "name": "Angular 6 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/angular-6-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "11 minutes",
            "description": "Multi-choice test that measures the knowledge of the basic components and modules of Angular 6 and concepts like data binding, dependency injection, CRUD with HTTP, typescript, routing and navigation.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:15.821284+00:00"
        },
        {
            "entity_id": "4021",
            "name": "AngularJS (New)",
            "link": "https://www.shl.com/products/product-catalog/view/angularjs-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of AngularJS architecture, forms, directives, filters, controllers, routing and testing.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:15.921835+00:00"
        },
        {
            "entity_id": "4030",
            "name": "Apache Hadoop (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-hadoop-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the knowledge of basic concepts of Hadoop, commands, HDFS and MapReduce.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:16.022341+00:00"
        },
        {
            "entity_id": "4011",
            "name": "Apache Hadoop Extensions (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-hadoop-extensions-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of Pig, Hive and HBase.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:16.122857+00:00"
        },
        {
            "entity_id": "4073",
            "name": "Apache HBase (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-hbase-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "5 minutes",
            "description": "Multi-choice test that measures the knowledge of HBase concepts such as CAP theorem, ACID properties, HBase client API, MapReduce integration, configuration and administration.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:16.223416+00:00"
        },
        {
            "entity_id": "4075",
            "name": "Apache Hive (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-hive-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "5 minutes",
            "description": "Multi-choice test that measures the knowledge of Hive architecture, datatypes, built-in functions, configurations, partitioning, bucketing and commands of Hive query language.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:21.815687+00:00"
        },
        {
            "entity_id": "4022",
            "name": "Apache Kafka (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-kafka-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "6 minutes",
            "description": "Multi-choice test that measures the knowledge of Apache Kafka architecture, components, clusters, performance tuning and advanced operations.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:22.162757+00:00"
        },
        {
            "entity_id": "4115",
            "name": "Apache Pig (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-pig-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "6 minutes",
            "description": "Multi-choice test that measures the knowledge of Pig architecture, built-in operators, built-in functions and commands in PigLatin.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:22.509671+00:00"
        },
        {
            "entity_id": "4023",
            "name": "Apache Spark (New)",
            "link": "https://www.shl.com/products/product-catalog/view/apache-spark-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the knowledge of Apache Spark principles, RDD operations - actions and transformations, lineage graphs and lazy evaluation.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:22.584375+00:00"
        },
        {
            "entity_id": "4017",
            "name": "ASP .NET with C# (New)",
            "link": "https://www.shl.com/products/product-catalog/view/asp-net-with-c-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multi-choice test that measures the knowledge of .NET framework and controls, C# fundamentals, OOPs concepts and advanced topics such as data access components, state management and security services.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:23.555099+00:00"
        },
        {
            "entity_id": "3786",
            "name": "ASP.NET 4.5",
            "link": "https://www.shl.com/products/product-catalog/view/asp-net-4-5/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "30 minutes",
            "description": "The ASP.NET 4.5 test measures knowledge of programming in the ASP.NET environment. Designed for experienced developers, but an average performer in this role should pass this test. This test includes the following topics: .NET Framework, Client-Side Programming, Data Access, Enhanced Runtime Features, Portals, Services and Mobile, Security, Troubleshooting and Optimization, Web Applications, and Web Forms.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:44:27.654495+00:00"
        },
        {
            "entity_id": "4219",
            "name": "Assessment and Development Center Exercises",
            "link": "https://www.shl.com/products/product-catalog/view/assessment-and-development-center-exercises/",
            "job_levels": ["Director","Entry-Level","Executive","Front Line Manager","General Population","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English International","English (USA)"],
            "duration": "Variable",
            "description": "SHL offers a comprehensive range of Assessment and Development Centre exercise in digital format, for remote assessment through our Virtual Assessment and Development Centre platform.",
            "keys": ["Assessment Exercises"],
            "scraped_at": "2026-05-08T10:44:28.869490+00:00"
        },
        {
            "entity_id": "3980",
            "name": "Automata - Fix (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automata-fix-new/",
            "job_levels": ["Mid-Professional"],
            "languages": ["English (USA)"],
            "duration": "20 minutes",
            "description": "A simulated compiler integrated test to measure debugging skills in C, C++ and Java. The test checks the ability to fix logical or syntactical errors and to reuse an existing code.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:14.380957+00:00"
        },
        {
            "entity_id": "3981",
            "name": "Automata - SQL (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automata-sql-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "30 minutes",
            "description": "A simulated query writing test that measures the ability to write SQL queries to perform DDL, DML and DCL tasks.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:23.941195+00:00"
        },
        {
            "entity_id": "3984",
            "name": "Automata (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automata-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "45 minutes",
            "description": "An AI-powered coding simulation assessment that evaluates candidate's programming ability. Offers a familiar IDE environment available in over 40 different programming languages.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:29.710587+00:00"
        },
        {
            "entity_id": "3982",
            "name": "Automata Data Science (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automata-data-science-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "60 minutes",
            "description": "A simulated test that measures the ability to analyze and modify data using machine learning algorithms to obtain desirable results.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:30.188693+00:00"
        },
        {
            "entity_id": "3983",
            "name": "Automata Data Science Pro (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automata-data-science-pro-new/",
            "job_levels": ["Professional Individual Contributor","Mid-Professional"],
            "languages": ["English (USA)"],
            "duration": "60 minutes",
            "description": "A simulated test that measures the ability to analyze and modify data using machine learning algorithms to obtain desirable results.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:39.976272+00:00"
        },
        {
            "entity_id": "4222",
            "name": "Automata Front End",
            "link": "https://www.shl.com/products/product-catalog/view/automata-front-end/",
            "job_levels": ["Entry-Level","Graduate","Mid-Professional","Professional Individual Contributor","Manager"],
            "languages": ["English (USA)"],
            "duration": "30 minutes",
            "description": "Simulation based test that measures the front-end development capabilities using HTML, CSS, and JavaScript. The candidate is provided with 3 different sections to code in HTML, CSS and JavaScript respectively.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:45.263696+00:00"
        },
        {
            "entity_id": "3985",
            "name": "Automata Pro (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automata-pro-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "60 minutes",
            "description": "An AI-powered coding simulation assessment that evaluates candidate's programming ability. Offers a familiar IDE environment available in over 40 different programming languages.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:52.192753+00:00"
        },
        {
            "entity_id": "4229",
            "name": "Automata Selenium",
            "link": "https://www.shl.com/products/product-catalog/view/automata-selenium/",
            "job_levels": ["Entry-Level","Graduate","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "60 minutes",
            "description": "A coding simulation assessment that evaluates the ability to conduct tasks related to automation testing using Selenium scripts.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:46:57.622235+00:00"
        },
        {
            "entity_id": "4026",
            "name": "Automation Anywhere RPA Development (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automation-anywhere-rpa-development-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the knowledge of Automation Anywhere dash board and task editor, control room, key commands, bots and Automation Anywhere client.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:47:03.274940+00:00"
        },
        {
            "entity_id": "4025",
            "name": "Automotive Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/automotive-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multi-choice test that measures the knowledge of auto engine classification, engine fuel system, auto-vehicle technology, maintenance, inspection and troubleshooting.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:47:09.607620+00:00"
        }
    ]

    # Add key assessments referenced in GenAI sample conversations
    additional_entries = [
        {
            "entity_id": "720",
            "name": "Occupational Personality Questionnaire OPQ32r",
            "link": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
            "job_levels": ["Professional Individual Contributor","Supervisor","Mid-Professional","Front Line Manager","General Population","Graduate","Manager","Director","Executive"],
            "languages": ["English International","French (Canada)","Portuguese","Chinese Simplified","Chinese Traditional","French (Belgium)","French","Polish","Slovak","Czech","Danish","Flemish","Dutch","Estonian","Finnish","German","Greek","Hungarian","Icelandic","Indonesian","Italian","Japanese","Korean","Latvian","Lithuanian","Norwegian","English (USA)","Arabic","Portuguese (Brazil)","Spanish","Latin American Spanish","Romanian","Russian","Serbian","Swedish","Thai","Turkish","Malay","Vietnamese"],
            "duration": "25 minutes",
            "description": "The SHL Occupational Personality Questionnaire, the OPQ32, is one of the most widely used and respected measures of workplace behavioural style in the world. It provides a clear framework for understanding the impact of personality on job performance.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:56:40.965790+00:00"
        },
        {
            "entity_id": "3971",
            "name": "SHL Verify Interactive G+",
            "link": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)","Chinese Traditional","Korean","Serbian","Slovak","Spanish","English International","Danish","Swedish","Norwegian","Finnish","Latvian","Lithuanian","Estonian","Portuguese","Hungarian","Thai","Czech","Polish","Turkish","Portuguese (Brazil)","Romanian","Latin American Spanish","Italian","French (Canada)","Chinese Simplified","Dutch","German","French","Russian","Indonesian","Greek","Japanese"],
            "duration": "36 minutes",
            "description": "SHL Verify Interactive G+ (SVIG+) is a test of general cognitive ability that also generates accurate assessments of three specific abilities: Deductive Reasoning, Inductive Reasoning, and Numerical Reasoning.",
            "keys": ["Ability & Aptitude"],
            "scraped_at": "2026-05-08T11:25:30.336611+00:00"
        },
        {
            "entity_id": "741",
            "name": "Graduate Scenarios",
            "link": "https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
            "job_levels": ["Manager","Mid-Professional","Professional Individual Contributor","Graduate"],
            "languages": ["English International"],
            "duration": "Untimed",
            "description": "Graduate Scenarios is a unique test of Managerial Judgement - an individual's ability to decide on effective ways of handling real life situations. It consists of hypothetical scenarios, each followed by several possible responses.",
            "keys": ["Biodata & Situational Judgment"],
            "scraped_at": "2026-05-08T10:53:56.481947+00:00"
        },
        {
            "entity_id": "205",
            "name": "Linux Programming (General)",
            "link": "https://www.shl.com/products/product-catalog/view/linux-programming-general/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "25 minutes",
            "description": "The Linux Programming (General) test measures knowledge of programming in a Linux environment. Designed for experienced programmers, this test covers the following topics: AutoConf/AutoMake, Makefiles, C Programming, C++, Debugging Programs, Linux Programming Concepts, Platform Independence, Revision Control, RPC/CORBA, and X Programming.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:06:31.999670+00:00"
        },
        {
            "entity_id": "4100",
            "name": "Networking and Implementation (New)",
            "link": "https://www.shl.com/products/product-catalog/view/networking-and-implementation-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the knowledge of networking devices, protocols, reference models, routing and implementation of networks.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:09:37.089605+00:00"
        },
        {
            "entity_id": "4219",
            "name": "Smart Interview Live Coding",
            "link": "https://www.shl.com/products/product-catalog/view/smart-interview-live-coding/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor","Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "Variable",
            "description": "Smart Interview Live Coding is a real-time online coding interview, with a compiler interface. It enables one-to-one, panel and group interviews.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:03:00.262448+00:00"
        },
        {
            "entity_id": "3986",
            "name": "SVAR Spoken English (US) (New)",
            "link": "https://www.shl.com/products/product-catalog/view/svar-spoken-english-us-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "-",
            "description": "An automated spoken English test that measures fluency, pronunciation, active listening, vocabulary, grammar and spoken English understanding.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T11:16:19.414279+00:00"
        },
        {
            "entity_id": "4189",
            "name": "Contact Center Call Simulation (New)",
            "link": "https://www.shl.com/products/product-catalog/view/contact-center-call-simulation-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "15 minutes",
            "description": "Simulation based test that measures the ability to handle customer concerns over a call by referring to standard process documents.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T10:49:11.466600+00:00"
        },
        {
            "entity_id": "3939",
            "name": "Entry Level Customer Serv - Retail & Contact Center",
            "link": "https://www.shl.com/products/product-catalog/view/entry-level-customer-serv-retail-and-contact-center/",
            "job_levels": ["Entry-Level"],
            "languages": ["Latin American Spanish","German","French","Chinese Simplified","Swedish","Arabic","English International","English (USA)","French (Canada)","Italian","Dutch","Norwegian","Finnish","Danish"],
            "duration": "19 minutes",
            "description": "The Precise Fit Entry Level Customer Service Solution (Retail/Contact Center) is for entry-level positions in which employees interact with customers by providing information or carrying out customer requests.",
            "keys": ["Personality & Behavior","Competencies"],
            "scraped_at": "2026-05-08T10:51:30.768011+00:00"
        },
        {
            "entity_id": "3933",
            "name": "Customer Service Phone Simulation",
            "link": "https://www.shl.com/products/product-catalog/view/customer-service-phone-simulation/",
            "job_levels": [],
            "languages": ["French (Canada)","Portuguese (Brazil)","Dutch","Italian","Spanish","French","Latin American Spanish","Chinese Simplified","English (Australia)","English International","English (USA)"],
            "duration": "20 minutes",
            "description": "As part of Contact Center Simulations, the Customer Service Phone Simulation is designed for entry-level positions in a contact center environment.",
            "keys": ["Biodata & Situational Judgment","Simulations"],
            "scraped_at": "2026-05-08T10:50:09.527471+00:00"
        },
        {
            "entity_id": "3946",
            "name": "SHL Verify Interactive - Numerical Reasoning",
            "link": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-numerical-reasoning/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["French","German","Italian","Dutch","Chinese Simplified","Danish","Finnish","Norwegian","Swedish","Estonian","Latvian","Lithuanian","English International","English (USA)","Czech","Polish","Latin American Spanish","Spanish","Thai","Japanese","Korean","Portuguese","Portuguese (Brazil)","Chinese Traditional","Hungarian","Indonesian","Russian","Romanian","Turkish","French (Canada)","Greek","Slovak","Serbian","Arabic"],
            "duration": "20 minutes",
            "description": "Assesses how the candidate comprehends numerical information in various formats.",
            "keys": ["Ability & Aptitude","Simulations"],
            "scraped_at": "2026-05-08T11:02:54.057659+00:00"
        },
        {
            "entity_id": "3992",
            "name": "Financial Accounting (New)",
            "link": "https://www.shl.com/products/product-catalog/view/financial-accounting-new/",
            "job_levels": ["Entry-Level","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the ability to post journal entries, classify items into assets and liabilities, analyze financial statements and calculate financial ratios.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:52:37.776565+00:00"
        },
        {
            "entity_id": "4149",
            "name": "Basic Statistics (New)",
            "link": "https://www.shl.com/products/product-catalog/view/basic-statistics-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of statistical methods, exploratory analysis, basics of probability, standard distributions and statistical testing.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:47:58.691568+00:00"
        },
        {
            "entity_id": "4084",
            "name": "Java 8 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/java-8-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "18 minutes",
            "description": "Multi-choice test that measures the knowledge of Java class design, exceptions, generics, collections, concurrency, JDBC and Java I/O fundamentals.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:52:48.918113+00:00"
        },
        {
            "entity_id": "4034",
            "name": "Core Java (Advanced Level) (New)",
            "link": "https://www.shl.com/products/product-catalog/view/core-java-advanced-level-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multi-choice test that measures the knowledge of basic Java constructs, OOP concepts, files and exception handling, and advanced Java concepts like generics, collections, threads, strings and concurrency.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:49:29.178098+00:00"
        },
        {
            "entity_id": "4143",
            "name": "Spring (New)",
            "link": "https://www.shl.com/products/product-catalog/view/spring-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of Spring core, AOP, IOC container and transactions.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:03:37.228633+00:00"
        },
        {
            "entity_id": "4144",
            "name": "SQL (New)",
            "link": "https://www.shl.com/products/product-catalog/view/sql-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of SQL queries, data manipulation and transaction processing.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:03:43.164590+00:00"
        },
        {
            "entity_id": "4126",
            "name": "RESTful Web Services (New)",
            "link": "https://www.shl.com/products/product-catalog/view/restful-web-services-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "12 minutes",
            "description": "Multi-choice test that measures the knowledge of REST features, architecture, handling requests, producing responses, entity translation, working with return types, security, filters, and interceptors.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:01:26.362905+00:00"
        },
        {
            "entity_id": "4059",
            "name": "Docker (New)",
            "link": "https://www.shl.com/products/product-catalog/view/docker-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of Docker container, data management, Docker performance and swarm.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:47:02.229413+00:00"
        },
        {
            "entity_id": "731",
            "name": "Dependability and Safety Instrument (DSI)",
            "link": "https://www.shl.com/products/product-catalog/view/dependability-and-safety-instrument-dsi/",
            "job_levels": ["Entry-Level"],
            "languages": ["Portuguese (Brazil)","Chinese Traditional","Danish","Dutch","Finnish","French","German","Icelandic","Chinese Simplified","English International","Italian","Latin American Spanish","Polish","Swedish","English (USA)","Norwegian","Russian"],
            "duration": "10 minutes",
            "description": "The DSI is a short pre-screening tool for many key entry-level roles. It is designed to identify potential employees who will have good dependability and reliability, and who are less likely to engage in counter-productive work behaviors.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:46:24.369610+00:00"
        },
        {
            "entity_id": "4068",
            "name": "Workplace Health and Safety (New)",
            "link": "https://www.shl.com/products/product-catalog/view/workplace-health-and-safety-new/",
            "job_levels": ["Entry-Level","Graduate","Manager","Supervisor","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of first aid, emergency safety measures, cleanliness and personal hygiene.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:18:11.120183+00:00"
        },
        {
            "entity_id": "331",
            "name": "HIPAA (Security)",
            "link": "https://www.shl.com/products/product-catalog/view/hipaa-security/",
            "job_levels": ["Front Line Manager","Manager"],
            "languages": ["English (USA)"],
            "duration": "15 minutes",
            "description": "The HIPAA (Security) test measures knowledge of compliance with the standards required by the Security and Electronic Signature Standards as they apply to HIPAA.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:54:27.187989+00:00"
        },
        {
            "entity_id": "4058",
            "name": "Medical Terminology (New)",
            "link": "https://www.shl.com/products/product-catalog/view/medical-terminology-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "3 minutes",
            "description": "Multi-choice test that measures the knowledge of different medical terms and abbreviations related to the human body, diseases and diagnosis.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:07:02.189145+00:00"
        },
        {
            "entity_id": "3993",
            "name": "MS Excel (New)",
            "link": "https://www.shl.com/products/product-catalog/view/ms-excel-new/",
            "job_levels": ["Entry-Level","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)","Spanish","French","Portuguese (Brazil)"],
            "duration": "6 minutes",
            "description": "Multi-choice test that measures the ability to use MS Excel to maintain, organize, analyze and present numeric data.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:09:08.398346+00:00"
        },
        {
            "entity_id": "3994",
            "name": "MS Word (New)",
            "link": "https://www.shl.com/products/product-catalog/view/ms-word-new/",
            "job_levels": ["Professional Individual Contributor","Supervisor","Mid-Professional","Entry-Level","Graduate","Manager"],
            "languages": ["Spanish","French","Portuguese (Brazil)","English (USA)"],
            "duration": "4 minutes",
            "description": "Multi-choice test that measures the ability to use MS Word to record and save textual information.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:56:24.677796+00:00"
        },
        {
            "entity_id": "4207",
            "name": "Microsoft Excel 365 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/microsoft-excel-365-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "35 minutes",
            "description": "The Microsoft Excel 365 simulation evaluates ability to perform certain operations in a simulated environment of MS Excel, and includes topics like Applying Formulas and Functions, Creating and Analyzing Data, Formatting Cells, etc.",
            "keys": ["Knowledge & Skills","Simulations"],
            "scraped_at": "2026-05-08T10:55:10.466416+00:00"
        },
        {
            "entity_id": "4210",
            "name": "Microsoft Word 365 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/microsoft-word-365-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "35 minutes",
            "description": "The Microsoft Word 365 simulation evaluates ability to perform certain operations in a simulated environment of Microsoft Word, and includes topics like Creating Content, Formatting, Proofreading, etc.",
            "keys": ["Simulations","Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:08:31.603871+00:00"
        },
        {
            "entity_id": "4212",
            "name": "Microsoft PowerPoint 365 - Essentials (New)",
            "link": "https://www.shl.com/products/product-catalog/view/microsoft-powerpoint-365-essentials-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "25 minutes",
            "description": "The Microsoft PowerPoint 365 - Essentials simulation evaluates ability to perform certain operations in a simulated environment of Microsoft PowerPoint.",
            "keys": ["Knowledge & Skills","Simulations"],
            "scraped_at": "2026-05-08T11:08:07.905819+00:00"
        },
        {
            "entity_id": "4206",
            "name": "Basic Computer Literacy (Windows 10) (New)",
            "link": "https://www.shl.com/products/product-catalog/view/basic-computer-literacy-windows-10-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "30 minutes",
            "description": "The Basic Computer Literacy (Windows 10) simulation measures knowledge of general computer terminology, processes, and applications.",
            "keys": ["Simulations","Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:47:52.665937+00:00"
        },
        {
            "entity_id": "724",
            "name": "Motivation Questionnaire MQM5",
            "link": "https://www.shl.com/products/product-catalog/view/motivation-questionnaire-mqm5/",
            "job_levels": ["Director","Entry-Level","Executive","Front Line Manager","General Population","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["Latin American Spanish","Portuguese (Brazil)","Latvian","Danish","Indonesian","Swedish","Turkish","Portuguese","French (Canada)","Japanese","Chinese Traditional","Flemish","French (Belgium)","Spanish","Finnish","French","German","Greek","Italian","Polish","Romanian","Russian","English International","English (USA)","Chinese Simplified","Dutch","Hungarian","Norwegian","Czech","Slovak","English (Australia)","Arabic","Korean"],
            "duration": "25 minutes",
            "description": "By understanding what motivates their staff, managers can unlock each individual's full potential. This questionnaire measures 18 dimensions of an individual's motivation.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:55:45.867959+00:00"
        },
        {
            "entity_id": "3899",
            "name": "Executive Scenarios",
            "link": "https://www.shl.com/products/product-catalog/view/executive-scenarios/",
            "job_levels": ["Director","Executive","Manager"],
            "languages": ["Italian","English (USA)","English International","Korean"],
            "duration": "Untimed",
            "description": "Executive Scenarios is a unique test of Managerial Judgement - an individual's ability to decide on effective ways of handling real life situations. It consists of hypothetical scenarios, each followed by several possible responses.",
            "keys": ["Biodata & Situational Judgment"],
            "scraped_at": "2026-05-08T10:52:15.464974+00:00"
        },
        {
            "entity_id": "742",
            "name": "Management Scenarios",
            "link": "https://www.shl.com/products/product-catalog/view/management-scenarios/",
            "job_levels": ["Front Line Manager","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["Italian","English International","Korean","Arabic"],
            "duration": "Untimed",
            "description": "Managerial Scenarios is a unique test of Managerial Judgement - an individual's ability to decide on effective ways of handling real life situations.",
            "keys": ["Biodata & Situational Judgment"],
            "scraped_at": "2026-05-08T10:53:32.917413+00:00"
        },
        {
            "entity_id": "4284",
            "name": "HiPo Assessment Report 2.0",
            "link": "https://www.shl.com/products/product-catalog/view/hipo-assessment-report-2-0/",
            "job_levels": [],
            "languages": [],
            "duration": "",
            "description": "Part of SHL's High Potential solution, the HIPO Assessment Report 2.0 helps organizations identify individuals with the strongest potential to succeed in senior and challenging roles.",
            "keys": ["Competencies","Personality & Behavior"],
            "scraped_at": "2026-05-08T10:51:21.676186+00:00"
        },
        {
            "entity_id": "3968",
            "name": "SHL Verify Interactive - Inductive Reasoning",
            "link": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-inductive-reasoning/",
            "job_levels": ["Professional Individual Contributor","Graduate","Manager","Mid-Professional"],
            "languages": ["Korean","Japanese","Thai","Portuguese (Brazil)","Portuguese","Chinese Traditional","Indonesian","Russian","Romanian","Polish","Greek","Latin American Spanish","English International","Arabic","Hungarian","Czech","French (Canada)","Slovak","Serbian","Turkish","Spanish","Danish","Estonian","Finnish","Latvian","Lithuanian","Norwegian","Swedish","French","German","Italian","Dutch","Chinese Simplified","English (USA)"],
            "duration": "20 minutes",
            "description": "Evaluates ability to identify specific patterns in data or situations and generalize that information to broader contexts.",
            "keys": ["Ability & Aptitude","Simulations"],
            "scraped_at": "2026-05-08T11:15:13.326130+00:00"
        },
        {
            "entity_id": "3947",
            "name": "SHL Verify Interactive - Deductive Reasoning",
            "link": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-deductive-reasoning/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["Chinese Traditional","Romanian","Turkish","Polish","Greek","Latin American Spanish","Portuguese (Brazil)","Japanese","Hungarian","Czech","French (Canada)","Slovak","Serbian","English International","English (USA)","German","Italian","Indonesian","Korean","Russian","Arabic","Danish","Finnish","Norwegian","Swedish","Estonian","Latvian","Lithuanian","French","Dutch","Chinese Simplified","Spanish","Portuguese"],
            "duration": "20 minutes",
            "description": "Measures the ability to draw logical conclusions based on information provided, identify strengths and weaknesses of arguments, and complete scenarios using incomplete information.",
            "keys": ["Ability & Aptitude","Simulations"],
            "scraped_at": "2026-05-08T11:02:47.581348+00:00"
        },
        {
            "entity_id": "3906",
            "name": "Verify - Verbal Ability - Next Generation",
            "link": "https://www.shl.com/products/product-catalog/view/verify-verbal-ability-next-generation/",
            "job_levels": ["General Population","Graduate","Executive","Director","Entry-Level","Manager","Mid-Professional","Professional Individual Contributor","Supervisor","Front Line Manager"],
            "languages": ["English (USA)","English International"],
            "duration": "15 minutes",
            "description": "The Verbal Ability test measures the ability to read written passages and comprehend the text, interpret tone and author intent, identify main ideas, and predict author responses.",
            "keys": ["Ability & Aptitude"],
            "scraped_at": "2026-05-08T11:05:36.987949+00:00"
        },
        {
            "entity_id": "4301",
            "name": "Global Skills Assessment",
            "link": "https://www.shl.com/products/product-catalog/view/global-skills-assessment/",
            "job_levels": [],
            "languages": ["Indonesian","Italian","Swedish","Thai","Portuguese (Brazil)","French (Canada)","Chinese Simplified","Danish","Finnish","French","German","English International","Japanese","Korean","Latin American Spanish","Norwegian","Polish","Romanian","Spanish","Vietnamese","Chinese Traditional","Arabic","English (USA)","Dutch","Portuguese","Turkish"],
            "duration": "16 minutes",
            "description": "The Global Skills Assessment (GSA) is an assessment used to measure 96 discrete skills/behaviors aligned to SHL's Universal Competency Framework (UCF).",
            "keys": ["Competencies","Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:53:56.055053+00:00"
        },
        {
            "entity_id": "4293",
            "name": "Manufac. & Indust. - Safety & Dependability 8.0",
            "link": "https://www.shl.com/products/product-catalog/view/safety-and-dependability-focus-8-0/",
            "job_levels": ["Entry-Level","Graduate","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)","German","Latin American Spanish","French","English International","Chinese Simplified","Italian","Japanese"],
            "duration": "16 minutes",
            "description": "The Manufacturing & Industrial Safety & Dependability Focus 8.0 Job-Focused Assessment measures the behaviors that underlie safe performance in a work setting.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:54:10.269684+00:00"
        },
        {
            "entity_id": "754",
            "name": "OPQ MQ Sales Report",
            "link": "https://www.shl.com/products/product-catalog/view/opq-mq-sales-report/",
            "job_levels": ["Director","Executive","Front Line Manager","General Population","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["Portuguese (Brazil)","Spanish","Danish","Dutch","Finnish","French (Canada)","French","German","Greek","Hungarian","Icelandic","Indonesian","Italian","Japanese","Korean","Latin American Spanish","Norwegian","Polish","Russian","Chinese Simplified","Swedish","Thai","Turkish","English International","English (USA)","Chinese Traditional","Portuguese","Romanian"],
            "duration": "",
            "description": "This OPQ (Occupational Personality Questionnaire) report provides a graphical and narrative summary of an individual's natural style that is critical to sales success.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:57:35.453951+00:00"
        },
        {
            "entity_id": "749",
            "name": "OPQ Leadership Report",
            "link": "https://www.shl.com/products/product-catalog/view/opq-leadership-report/",
            "job_levels": ["Director","Executive","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["Dutch","English International","English (USA)","Romanian","Portuguese","French","German","Swedish","Chinese Simplified","Portuguese (Brazil)","Japanese","Polish","Russian","Latin American Spanish"],
            "duration": "",
            "description": "This OPQ (Occupational Personality Questionnaire) report provides a detailed analysis of an individual's leadership potential.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T10:57:06.790575+00:00"
        },
        {
            "entity_id": "4289",
            "name": "OPQ Universal Competency Report 2.0",
            "link": "https://www.shl.com/products/product-catalog/view/opq-universal-competency-report-2-0/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor","Director","Executive","Front Line Manager","General Population"],
            "languages": [],
            "duration": "",
            "description": "This OPQ (Occupational Personality Questionnaire) report is based on the Universal Competency framework.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T11:10:54.641242+00:00"
        },
        {
            "entity_id": "4283",
            "name": "Sales Transformation 2.0 - Individual Contributor",
            "link": "https://www.shl.com/products/product-catalog/view/salestransformationreport2-0-individualcontributor/",
            "job_levels": ["Front Line Manager","General Population","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": [],
            "duration": "",
            "description": "This report draws insights from the OPQ. It provides an accurate and objective measure of a salesperson's ability to sell well in a digital first environment.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T11:25:24.957825+00:00"
        },
        {
            "entity_id": "4201",
            "name": "Typing (New)",
            "link": "https://www.shl.com/products/product-catalog/view/typing-new/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)"],
            "duration": "2 minutes",
            "description": "Typing based test that evaluates typing speed and accuracy.",
            "keys": ["Simulations"],
            "scraped_at": "2026-05-08T11:16:59.973554+00:00"
        },
        {
            "entity_id": "4123",
            "name": "Python (New)",
            "link": "https://www.shl.com/products/product-catalog/view/python-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "11 minutes",
            "description": "Multi-choice test that measures the knowledge of Python programming, databases, modules and library.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:12:27.171543+00:00"
        },
        {
            "entity_id": "4177",
            "name": "ReactJS (New)",
            "link": "https://www.shl.com/products/product-catalog/view/reactjs-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the technical knowledge of React APIs, render function, JSX, form validation and styling.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:00:58.363011+00:00"
        },
        {
            "entity_id": "3989",
            "name": "JavaScript (New)",
            "link": "https://www.shl.com/products/product-catalog/view/javascript-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures knowledge of programming in the JavaScript language and its application in front-end development.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:53:07.008961+00:00"
        },
        {
            "entity_id": "3997",
            "name": "Node.js (New)",
            "link": "https://www.shl.com/products/product-catalog/view/node-js-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the basic knowledge of Node.js such as events, streams, file system, error handling, concurrency, DB handling and express framework.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:09:43.600924+00:00"
        },
        {
            "entity_id": "4035",
            "name": "SQL Server (New)",
            "link": "https://www.shl.com/products/product-catalog/view/sql-server-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "11 minutes",
            "description": "Multi-choice test that measures the knowledge of basic SQL queries, creating and altering tables, filtering, grouping, aggregation in SQL and querying multiple tables.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:15:41.690976+00:00"
        },
        {
            "entity_id": "4010",
            "name": "MongoDB (New)",
            "link": "https://www.shl.com/products/product-catalog/view/mongodb-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of MongoDB like sharding, replication, indexing, security and storage.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:55:39.756504+00:00"
        },
        {
            "entity_id": "729",
            "name": "Count Out The Money",
            "link": "https://www.shl.com/products/product-catalog/view/count-out-the-money/",
            "job_levels": ["Entry-Level"],
            "languages": ["English (USA)","English (Australia)","English (Canada)","English International","English (South Africa)"],
            "duration": "5 minutes",
            "description": "The Count out the Money -US test measures a candidate's money handling ability.",
            "keys": ["Knowledge & Skills","Simulations"],
            "scraped_at": "2026-05-08T10:49:47.413492+00:00"
        },
        {
            "entity_id": "4138",
            "name": "Selenium (New)",
            "link": "https://www.shl.com/products/product-catalog/view/selenium-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of Selenium IDE, Selenium RC, Selenium grid, web driver, test design considerations, user extensions, frameworks and object repository.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:02:36.776339+00:00"
        },
        {
            "entity_id": "4091",
            "name": "Microservices (New)",
            "link": "https://www.shl.com/products/product-catalog/view/microservices-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the knowledge of Microservices architecture, SOA, and Microservices patterns.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:07:41.977663+00:00"
        },
        {
            "entity_id": "4038",
            "name": "C Programming (New)",
            "link": "https://www.shl.com/products/product-catalog/view/c-programming-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of C programming basics, functions, arrays, composed data types, and advanced C concepts like SLF, file handling and dynamic memory.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:48:35.298637+00:00"
        },
        {
            "entity_id": "4039",
            "name": "C# Programming (New)",
            "link": "https://www.shl.com/products/product-catalog/view/c-programming-new-4039/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of C# programming structure, functions, collections, enumeration, exception handling, OOPs constructs, inheritance, event handling and operator overloading.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:45:03.676398+00:00"
        },
        {
            "entity_id": "4122",
            "name": "C++ Programming (New)",
            "link": "https://www.shl.com/products/product-catalog/view/c-programming-new-4122/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of programming in the C++ language and the ability to use the C++ standard library to write code.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:45:23.172996+00:00"
        },
        {
            "entity_id": "4080",
            "name": "HTML/CSS (New)",
            "link": "https://www.shl.com/products/product-catalog/view/htmlcss-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "12 minutes",
            "description": "Multi-choice test that measures the knowledge of HTML to create a user interface and CSS to stylize it.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:54:50.821524+00:00"
        },
        {
            "entity_id": "4152",
            "name": "Kubernetes (New)",
            "link": "https://www.shl.com/products/product-catalog/view/kubernetes-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "6 minutes",
            "description": "Multi-choice test that measures the knowledge of the architecture, cluster and services of Kubernetes.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:04:28.174366+00:00"
        },
        {
            "entity_id": "3990",
            "name": "Linux Administration (New)",
            "link": "https://www.shl.com/products/product-catalog/view/linux-administration-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures knowledge of the Linux operating system and its application in system administration and network administration.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:04:37.760817+00:00"
        },
        {
            "entity_id": "4081",
            "name": "HTML5 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/html5-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "11 minutes",
            "description": "Multi-choice test that measures the knowledge of HTML5 and its application in creating a user interface.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:51:42.549846+00:00"
        },
        {
            "entity_id": "4052",
            "name": "CSS3 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/css3-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the knowledge of CSS3 and its application in providing style to web documents.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:49:53.845859+00:00"
        },
        {
            "entity_id": "4104",
            "name": "Computer Science (New)",
            "link": "https://www.shl.com/products/product-catalog/view/computer-science-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "12 minutes",
            "description": "Multi-choice test that measures the knowledge of operating system, computer architecture, DBMS and basics of computer networks and communication.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:24:35.817873+00:00"
        },
        {
            "entity_id": "4045",
            "name": "Cloud Computing (New)",
            "link": "https://www.shl.com/products/product-catalog/view/cloud-computing-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the knowledge of cloud computing concepts, cloud service models, virtualization and private clouds.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:48:58.977171+00:00"
        },
        {
            "entity_id": "4077",
            "name": "Cardiology and Diabetes Management (New)",
            "link": "https://www.shl.com/products/product-catalog/view/cardiology-and-diabetes-management-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "4 minutes",
            "description": "Multi-choice test that measures the knowledge of how to control and manage cardiovascular diseases and diabetes.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:45:29.976861+00:00"
        },
        {
            "entity_id": "310",
            "name": "Business Communication (adaptive)",
            "link": "https://www.shl.com/products/product-catalog/view/business-communication-adaptive/",
            "job_levels": ["Entry-Level","Front Line Manager","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "24 minutes",
            "description": "This is an adaptive test that measures knowledge of communicating in the workplace. It measures the skills necessary to communicate effectively with coworkers at all levels.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:48:23.147138+00:00"
        },
        {
            "entity_id": "4053",
            "name": "Cyber Risk (New)",
            "link": "https://www.shl.com/products/product-catalog/view/cyber-risk-new/",
            "job_levels": ["Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the knowledge of cyber risk management, system and application security, network security and security management.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:50:21.497794+00:00"
        },
        {
            "entity_id": "4013",
            "name": "Data Science (New)",
            "link": "https://www.shl.com/products/product-catalog/view/data-science-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "14 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge on how to use machine learning to analyze data, extract information, draw conclusions and make statistically-driven decisions.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:46:11.570260+00:00"
        },
        {
            "entity_id": "56",
            "name": "Data Warehousing Concepts",
            "link": "https://www.shl.com/products/product-catalog/view/data-warehousing-concepts/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "25 minutes",
            "description": "The Data Warehousing Concepts test measures knowledge of Data Warehousing.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:46:17.780050+00:00"
        },
        {
            "entity_id": "219",
            "name": "Programming Concepts",
            "link": "https://www.shl.com/products/product-catalog/view/programming-concepts/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "25 minutes",
            "description": "The Programming Concepts test measures knowledge of the core aspects of computer science programming that is valid across programming languages.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:12:02.768884+00:00"
        },
        {
            "entity_id": "3769",
            "name": "Project Management (2013)",
            "link": "https://www.shl.com/products/product-catalog/view/project-management-2013/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "30 minutes",
            "description": "The Project Management (2013) test measures knowledge of how to manage projects to ensure that objectives are completed on time and within budget.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:12:16.337338+00:00"
        },
        {
            "entity_id": "4055",
            "name": "Informatica (Developer) (New)",
            "link": "https://www.shl.com/products/product-catalog/view/informatica-developer-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "11 minutes",
            "description": "Multi-choice test that measures the knowledge of data warehousing, server architecture and administration, and real time implementation with Informatica.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:03:32.349644+00:00"
        },
        {
            "entity_id": "4086",
            "name": "Jenkins (New)",
            "link": "https://www.shl.com/products/product-catalog/view/jenkins-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "6 minutes",
            "description": "Multi-choice test that measures the knowledge of Jenkins configuration and deployment, plugins, nodes, build jobs and testing.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:04:15.210690+00:00"
        },
        {
            "entity_id": "4087",
            "name": "jQuery (New)",
            "link": "https://www.shl.com/products/product-catalog/view/jquery-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of jQuery events and effects, jQuery animation, UI, references, and using jQuery with AJAX.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:53:20.510302+00:00"
        },
        {
            "entity_id": "4157",
            "name": "Manual Testing (New)",
            "link": "https://www.shl.com/products/product-catalog/view/manual-testing-new/",
            "job_levels": ["Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of the software testing life cycle, testing tools and techniques, design of test cases and generation of test reports.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:06:44.239787+00:00"
        },
        {
            "entity_id": "4008",
            "name": "Marketing (New)",
            "link": "https://www.shl.com/products/product-catalog/view/marketing-new/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)"],
            "duration": "9 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of marketing principles, market research, consumer behavior, brand management, sales management, channel management and advertisement management.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:54:26.378612+00:00"
        },
        {
            "entity_id": "3999",
            "name": "Human Resources (New)",
            "link": "https://www.shl.com/products/product-catalog/view/human-resources-new/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the candidate on his/her knowledge and understanding of the basic concepts of Human Resources Management.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:51:48.967097+00:00"
        },
        {
            "entity_id": "4006",
            "name": "Mechanical Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/mechanical-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of fluid and machine mechanics, thermodynamics, IC engines and manufacturing science.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:54:39.368407+00:00"
        },
        {
            "entity_id": "4009",
            "name": "Economics (New)",
            "link": "https://www.shl.com/products/product-catalog/view/economics-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of microeconomics, macroeconomics and international trade.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:50:48.472942+00:00"
        },
        {
            "entity_id": "4031",
            "name": "Electrical Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/electrical-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the knowledge of basic electrical engineering, electrical machines, power systems, instrumentation, control systems and basic concepts of electronics.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:50:53.366784+00:00"
        },
        {
            "entity_id": "4007",
            "name": "Instrumentation Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/instrumentation-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "12 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of instrumentation, electronics, signals and communication systems.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:03:38.865061+00:00"
        },
        {
            "entity_id": "726",
            "name": "Sales Interview Guide",
            "link": "https://www.shl.com/products/product-catalog/view/sales-interview-guide/",
            "job_levels": ["Director","Entry-Level","Executive","Front Line Manager","Manager","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English International"],
            "duration": "Untimed",
            "description": "The SHL Sales Model is mapped to the SHL Universal Competency Model (UCF). The Sales Model Interview guide was developed to enable you to use the Sales Report more effectively.",
            "keys": ["Personality & Behavior"],
            "scraped_at": "2026-05-08T11:25:14.079572+00:00"
        },
        {
            "entity_id": "4014",
            "name": "Social Media (New)",
            "link": "https://www.shl.com/products/product-catalog/view/social-media-new/",
            "job_levels": ["Entry-Level","Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge about the different social media platforms.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:15:30.923687+00:00"
        },
        {
            "entity_id": "4042",
            "name": "Polymer Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/polymer-engineering-new/",
            "job_levels": ["Professional Individual Contributor","Graduate","Mid-Professional"],
            "languages": ["English (USA)"],
            "duration": "8 minutes",
            "description": "Multi-choice test that measures the knowledge of characterization of polymers, processing, synthesis, testing and applications in daily life.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T11:11:21.166970+00:00"
        },
        {
            "entity_id": "3995",
            "name": "MS Office Basic Computer Literacy (New)",
            "link": "https://www.shl.com/products/product-catalog/view/ms-office-basic-computer-literacy-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)","Spanish","Portuguese (Brazil)","French"],
            "duration": "7 minutes",
            "description": "Multi-choice test that measures the ability to use MS Word, MS Excel and MS PowerPoint to perform basic tasks on a computer.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:56:08.827295+00:00"
        },
        {
            "entity_id": "4204",
            "name": "RemoteWorkQ",
            "link": "https://www.shl.com/products/product-catalog/view/remoteworkq/",
            "job_levels": ["Manager","Mid-Professional","Professional Individual Contributor","Supervisor","Front Line Manager","General Population","Graduate","Director","Entry-Level","Executive"],
            "languages": ["English (USA)","Arabic","Italian","Chinese Simplified","Portuguese","Turkish","Portuguese (Brazil)","Indonesian","English International","Spanish","Latin American Spanish","French (Canada)","German","Dutch","French"],
            "duration": "10 minutes",
            "description": "Using the Apta Architecture to focus on the relevant competency behaviors in the Universal Competency Framework, SHL developed the RemoteWorkQ to measure self-reported behavioral tendencies in competency areas important for remote work.",
            "keys": ["Competencies"],
            "scraped_at": "2026-05-08T11:12:37.930744+00:00"
        },
        {
            "entity_id": "4150",
            "name": "Civil Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/civil-engineering-new/",
            "job_levels": ["Graduate","Manager","Mid-Professional","Professional Individual Contributor","Supervisor"],
            "languages": ["English (USA)"],
            "duration": "10 minutes",
            "description": "Multi-choice test that measures the knowledge of structural engineering, transportation engineering, surveying, geotechnical engineering and water resources engineering.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:48:52.279789+00:00"
        },
        {
            "entity_id": "4012",
            "name": "Chemical Engineering (New)",
            "link": "https://www.shl.com/products/product-catalog/view/chemical-engineering-new/",
            "job_levels": ["Graduate","Mid-Professional","Professional Individual Contributor"],
            "languages": ["English (USA)"],
            "duration": "13 minutes",
            "description": "Multi-choice test that measures the conceptual knowledge of transport phenomena, chemical process engineering and technology, chemical process principles, stoichiometry and process calculations.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:48:47.002853+00:00"
        },
        {
            "entity_id": "4036",
            "name": "Biotech Lab Techniques (New)",
            "link": "https://www.shl.com/products/product-catalog/view/biotech-lab-techniques-new/",
            "job_levels": ["Graduate","Professional Individual Contributor","Mid-Professional"],
            "languages": ["English (USA)"],
            "duration": "5 minutes",
            "description": "Multi-choice test that measures the knowledge of biophysical techniques, bio-processing and separation techniques like chromatography and electrophoresis.",
            "keys": ["Knowledge & Skills"],
            "scraped_at": "2026-05-08T10:48:11.376481+00:00"
        }
    ]

    all_entries = entries + additional_entries

    # Normalize
    normalized = [normalize_entry(item) for item in all_entries]

    # Write output
    output_path = Path("data/catalog.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(normalized)} normalized entries to {output_path}")

    # Show summary by test_type
    from collections import Counter
    type_counts = Counter(e["test_type"] for e in normalized)
    logger.info(f"Test type distribution: {dict(type_counts)}")


if __name__ == "__main__":
    main()
