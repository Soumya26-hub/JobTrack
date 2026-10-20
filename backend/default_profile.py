"""Starting resume profile, taken from my resume. It can be edited in the app."""

DEFAULT_PROFILE = {
    "intro": "Software professional with nearly two years at Zifo",
    "skills": (
        "Python, SQL, JavaScript, C programming, FastAPI, REST APIs, SQLAlchemy ORM, "
        "SQLite, HTML, CSS, Camunda Modeler, BPMN, GitLab CI/CD pipelines, Git, GitHub, "
        "LabVantage, LIMS, ELN, master data management, life sciences, Microsoft Excel, "
        "Visual Studio Code, AI-assisted development, data validation, client demonstrations"
    ),
    # One highlight per line. The agent picks the lines that best match each job.
    "highlights": "\n".join([
        "Automates ELN and LIMS processes that support laboratory operations for life sciences clients",
        "Designs and modifies BPMN workflows in Camunda Modeler, configuring topics, inputs and variables",
        "Runs and monitors GitLab CI/CD pipelines to deploy and test automation releases",
        "Built Python scripts that automate the generation of calculation scripts from master data",
        "Maintains and validates master data in LabVantage and Microsoft Excel",
        "Built StudyTrack, a full-stack application with a FastAPI backend, REST APIs, SQLAlchemy ORM and SQLite",
        "Builds responsive web pages with HTML, CSS and JavaScript",
        "Uses AI coding assistants to draft logic and scripts, then reviews and refines the output",
        "Presents solutions in client demonstrations and turns client feedback into changes",
        "Holds a Certificate in Software Development Engineering with Applied AI (8.9 CGPA)",
        "Brings life sciences domain knowledge from a postgraduate degree in Plant Biology and Plant Biotechnology",
    ]),
}
