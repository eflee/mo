"""XML builder for NFO files with proper encoding and formatting."""

import xml.etree.ElementTree as ET
from typing import Any, Optional
from xml.dom import minidom


class NFOBuilder:
    """Builder for creating NFO XML files with proper Jellyfin formatting."""

    def __init__(self, root_tag: str):
        """Initialize NFO builder with a root element.

        Args:
            root_tag: Name of the root XML element (e.g., "movie", "tvshow", "episodedetails")
        """
        self.root = ET.Element(root_tag)

    def add_element(
        self,
        tag: str,
        text: Optional[Any] = None,
        parent: Optional[ET.Element] = None,
        **attributes: str,
    ) -> ET.Element:
        """Add an element to the NFO.

        Args:
            tag: Element tag name
            text: Text content (will be converted to string, None values are skipped)
            parent: Parent element (defaults to root)
            **attributes: Element attributes

        Returns:
            ET.Element: The created element
        """
        if parent is None:
            parent = self.root

        element = ET.SubElement(parent, tag, **attributes)

        if text is not None:
            element.text = str(text)

        return element

    def add_elements(
        self,
        tag: str,
        values: list,
        parent: Optional[ET.Element] = None,
    ) -> list[ET.Element]:
        """Add multiple elements with the same tag.

        Args:
            tag: Element tag name
            values: List of text values
            parent: Parent element (defaults to root)

        Returns:
            list[ET.Element]: List of created elements
        """
        elements = []
        for value in values:
            if value is not None:
                element = self.add_element(tag, value, parent)
                elements.append(element)
        return elements

    def to_string(self, pretty: bool = True) -> str:
        """Convert the NFO to an XML string.

        Args:
            pretty: Enable pretty-printing with indentation

        Returns:
            str: XML string with UTF-8 encoding declaration
        """
        if pretty:
            # Use minidom for pretty-printing
            rough_string = ET.tostring(self.root, encoding="unicode")
            reparsed = minidom.parseString(rough_string)
            # Get pretty XML without the XML declaration from minidom
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding=None)

            # Remove extra blank lines and the default XML declaration
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            # Filter out the xml declaration line from minidom
            lines = [line for line in lines if not line.strip().startswith('<?xml')]

            # Add proper XML declaration and join
            xml_declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            return xml_declaration + '\n' + '\n'.join(lines)
        else:
            # Return compact XML
            xml_declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            tree_string = ET.tostring(self.root, encoding="unicode")
            return xml_declaration + tree_string

    def write(self, filepath: str, pretty: bool = True) -> None:
        """Write the NFO to a file.

        Args:
            filepath: Path to output file
            pretty: Enable pretty-printing with indentation
        """
        xml_string = self.to_string(pretty=pretty)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_string)
