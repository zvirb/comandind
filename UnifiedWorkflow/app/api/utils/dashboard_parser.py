"""A utility to parse a markdown checklist file into a structured format for the dashboard."""

import re
import logging
from typing import List, TypedDict

# Setup logging
logger = logging.getLogger(__name__)


class TaskDict(TypedDict):
    """A dictionary representing a single task."""
    description: str
    status_icon: str
    progress: int


class SectionDict(TypedDict):
    """A dictionary representing a section with its tasks."""
    title: str
    tasks: List[TaskDict]


def parse_progress_checklist_markdown(
    file_path: str = "/project/docs/PROGRESS_CHECKLIST.txt"
) -> List[SectionDict]:
    """
    Parses the PROGRESS_CHECKLIST.txt file into a structured list of dictionaries.

    Args:
        file_path: The absolute path to the PROGRESS_CHECKLIST.txt file.

    Returns:
        A list of dictionaries, where each dictionary represents a section and its tasks.
    """
    sections_data: List[SectionDict] = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Regex to find sections starting with "## I. Title", "## II. Title", etc.
        # Captures: 1=Roman Numeral, 2=Title, 3=Content of the section
        section_regex = re.compile(
            r"^\s*##\s*([IVXLCDM]+)\.\s(.*?)\r?\n([\s\S]*?)(?=\r?\n\s*##\s*[IVXLCDM]+\.\s|$)",
            re.MULTILINE | re.IGNORECASE,
        )

        # Regex to find GitHub-flavored markdown tasks including [-] for in-progress
        # Captures: 1=checkbox state ('x', ' ', '-') , 2=task description
        task_line_regex = re.compile(r"^\s*-\s\[([x\s-])\]\s*(.*)", re.MULTILINE)

        for section_match in section_regex.finditer(markdown_content):
            title = section_match.group(2).strip()
            content = section_match.group(3)
            tasks: List[TaskDict] = []

            for task_match in task_line_regex.finditer(content):
                checkbox_state = task_match.group(1)
                description = task_match.group(2).strip()
                status_icon = '🔲'
                progress = 0

                if checkbox_state == 'x':
                    status_icon = '✅'
                    progress = 100
                elif checkbox_state == '-':
                    status_icon = '🟡'
                    progress = 50
                # else it remains '🔲' and 0

                tasks.append({
                    "description": description,
                    "status_icon": status_icon,
                    "progress": progress
                })

            # Only add sections that actually contain tasks
            if tasks:
                sections_data.append({"title": title, "tasks": tasks})

    except FileNotFoundError:
        logger.error(
            "Dashboard parser: PROGRESS_CHECKLIST.txt not found at %s",
            file_path,
            exc_info=True,
        )
        return []
    except IOError as e:
        logger.error(
            "Dashboard parser: IO error reading file %s: %s", file_path, e, exc_info=True
        )
        return []
    except (AttributeError, TypeError, ValueError, re.error) as e:
        logger.error(
            "Dashboard parser: An unexpected error occurred parsing the markdown file: %s",
            e,
            exc_info=True,
        )
        return []

    return sections_data
