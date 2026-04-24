from colorama import Fore # print colors in the console
import dataclasses  # for efficient access to classes containing mainly data
from enum import Enum  # enumeration classes
from kraken.lib import xml
import numpy as np  # matrix manipulation
import shapely  # Polygons

from glossit_dataclasses import RegionType, LineType, Region, MainTextLine, GlossLine, MAIN_TEXT_LINE_TYPES
from xml_extraction import METSPage


@dataclasses.dataclass(frozen=True)
class ColoredString:
    """
    Class ColoredString represents a colored string. When converted to a string, the label is printed using the color
    scheme.

    Attributes:
        label (str): The text string.
        color (colorama.Fore): The colorama.Fore coloring string.
    """
    string: str
    color: str  # (colorama.Fore)

    def __repr__(self) -> str:
        return f"Status(string='{self.string}')"

    def __str__(self) -> str:
        return f"{self.color}{self.string}{Fore.RESET}"


class CheckStatus(Enum):
    """
    Class CheckStatus encapsulates the status of a check, i.e., whether the result is good, you should be warned about
    it and check manually, or if a critical check has failed.

    Attributes:
        GOOD (ColoredString): This should be returned if the test has passed.
        INFO (ColoredString): If such tests have failed, this is merely an information, since perfectly fine annotated
                              pages may have multiple such occurrences.
        WARNING (ColoredString): This indicates that the test has failed in a way that indicates something
                                 has gone wrong, but also, perfectly fine annotated pages can sometimes fail this test.
        CRITICAL (ColoredString): The test has failed critically, immediate action must be taken.

    Methods:
        get_string: Returns the plain string contained in the ColoredString object.
    """
    GOOD = ColoredString("GOOD", Fore.GREEN)
    INFO = ColoredString("INFO", Fore.WHITE)
    WARNING = ColoredString("WARNING", Fore.YELLOW)
    CRITICAL = ColoredString("CRITICAL", Fore.RED)

    def __str__(self) -> str:
        return str(self.value)

    def get_string(self) -> str:
        """
        Returns the plain string contained in the ColoredString object.
        :return: The plain string.
        """
        return self.value.string

    def decorator(self, func):
        """
        When called with a function func, it sets the keyword argument return_type to be this instance's value.

        :param func: function with keyword argument return_type
        :return: Sets the keyword argument return_type to be this instance's value.
        """
        def wrapper(*args, **kwargs):
            return func(*args, return_type=self, **kwargs)
        return wrapper


@dataclasses.dataclass
class CheckResult:
    """
    Class CheckResult encapsulates a result of a single sanity check.

    Attributes:
        status (CheckStatus): If True, the test was passed.
        name (str): The test's name (or a very short description).
        error_description (str): Description of the errors occurring in the test.
        erroneous_instances (list): List of the lines/regions that are erroneous.
        verbose_description (str): More detailed description of the errors occurring in the test.

    Methods:
        to_console_string (bool): Returns a beautiful colored string for the console containing the test result.
        to_plain_string (bool): Returns an ordinary plain text string containing the test result.

    """
    def __init__(self,
                 status: CheckStatus,
                 name: str,
                 error_description: str,
                 verbose_description: str,
                 erroneous_instances: list,
                 error_polygons: list[list[tuple[int, int]]] = None):
        """
        Initialize a CheckResult instance.

        :param status: If True, the test was passed.
        :param name: The test's name.
        :param error_description: Description of the errors occurring in the test.
        :param verbose_description: More detailed description of the errors occurring in the test.
        :param erroneous_instances (list): List of the lines/regions that are erroneous.
        :param error_polygons: The polygons that contain the error, can be used for plotting the error.
        """
        self.status = status
        self.name = name
        self.error_description = error_description
        self.verbose_description = verbose_description
        self.erroneous_instances = erroneous_instances
        self.error_polygons = error_polygons

    def __repr__(self) -> str:
        return f"<CheckResult(status={self.status}, name={self.name}, error_description={self.error_description})>"

    def to_console_string(self, verbose_output: bool=False) -> str:
        """
        This method allows a beautiful, colored string for the console to be returned from the test result.

        :param verbose_output: If True, more detailed output is returned.
        :return: The pretty console string containing the test result.
        """
        if self.status == CheckStatus.GOOD:
            return f'    {self.status} ({self.name})'
        else:
            if verbose_output:
                return f'    {self.status} ({self.name})\n        {self.verbose_description}'
            else:
                return f'    {self.status} ({self.name})\n        {self.error_description}'

    def to_plain_string(self, verbose_output: bool=False) -> str:
        """
        This method returns an ordinary plain text string from the test result.

        :param verbose_output: If True, more detailed output is returned.
        :return: The plain text string containing the test result.
        """
        if self.status == CheckStatus.GOOD:
            return f'    {self.status.get_string()} ({self.name})'
        else:
            if verbose_output:
                return f'    {self.status.get_string()} ({self.name})\n        {self.verbose_description}'
            else:
                return f'    {self.status.get_string()} ({self.name})\n        {self.error_description}'


class RegionChecks:
    """
    In class RegionChecks, we collect the sanity checks that are related to regions.

    The checks are grouped into three classes:
        * CRITICAL: Those checks must never fail, as failure indicates severe errors.
        * WARNING: Failing these checks indicates errors, but there may be perfectly fine examples where the test fails.
        * INFO: Failing such tests occurs very often even in fine examples, so it is to be taken as additional
                information.
    If the check is passed (excluding INFO checks), CheckStatus.GOOD is returned.

    Attributes:
        regions (list[Region]): The list of regions the tests should be conducted on.
        is_double_page (bool): True if the page is a double page.

    Methods:
        check: Runs all checks and returns a list of CheckResult.

    Private Methods:
        _region_check_type: Check if the region type is a valid identifier. CRITICAL.
        _region_check_uniqueness: Check if the region types across all regions are unique. CRITICAL.
        _region_check_area: Check if the area of the region is plausibly large. WARNING.
        _region_check_intersection: Check that no two regions intersect each other. INFO.
    """
    def __init__(self, page: METSPage):
        """
        Initialize a RegionChecks instance.

        :param page: The METSPage on which the checks should be performed on.
        """
        self.regions = page.get_regions()
        self.is_double_page = page.is_double_page

    def check(self) -> list[CheckResult]:
        """
        Performs the checks and returns the test results as a list of CheckResult.

        :return: Test results.
        """
        region_checks = [
            self._region_check_type,
            self._region_check_uniqueness,
            self._region_check_area,
            self._region_check_intersection
        ]

        return [check_function() for check_function in region_checks]

    @CheckStatus.CRITICAL.decorator
    def _region_check_type(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the region type is a valid identifier.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_regions = []

        for region in self.regions:
            if region.type not in dataclasses.astuple(RegionType()):
                faulty_regions.append(region)

        success = (len(faulty_regions) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following regions have invalid region types:"
            verbose_description = error_description
            for region in faulty_regions:
                error_description +=   f"\n           {region}"
                verbose_description += f"\n           {region} has invalid type '{region.type}'"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Region types are valid",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_regions,
            error_polygons=[region.coordinates.exterior.coords for region in faulty_regions],
        )

    @CheckStatus.CRITICAL.decorator
    def _region_check_uniqueness(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if there are no two regions that have the same region type. Except for double-page manuscripts.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        types = [region.type for region in self.regions]

        region_types_dict = {}
        for region in self.regions:
            if region.type not in region_types_dict:
                region_types_dict[region.type] = 0
            region_types_dict[region.type] += 1

        page_threshold = 2 if self.is_double_page else 1  # double-page manuscripts will have doubled regions

        faulty_regions = [region for region in self.regions if region_types_dict[region.type] > page_threshold]
        success = (len(faulty_regions) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            if self.is_double_page:
                error_description += f"Following region types occur more than twice:"
            else:
                error_description += f"Following region types occur more than once:"
            verbose_description = error_description
            for region_type in region_types_dict:
                if region_types_dict[region_type] > page_threshold:
                    error_description +=   f"\n           '{region_type}': {region_types_dict[region_type]} times"
                    verbose_description += (
                        f"\n           '{region_type}': {region_types_dict[region_type]} times "
                        f"(regions {[region for region in self.regions if region.type == region_type]})"
                    )

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Region types appear only once (or twice for double-page manuscripts)",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_regions,
            error_polygons=[region.coordinates.exterior.coords for region in faulty_regions],
        )

    @CheckStatus.WARNING.decorator
    def _region_check_area(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the relative area of the region (region area divided by total page area) is plausibly large.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_regions = []

        area_threshold = 0.01 #%

        for region in self.regions:
            if region.relative_area * 100 < area_threshold:
                faulty_regions.append(region)

        success = (len(faulty_regions) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following regions have suspiciously small relative area:"
            verbose_description = error_description
            for region in faulty_regions:
                error_description +=   f"\n            {region}: {region.relative_area * 100:.4f}%"
                verbose_description += (f"\n            {region}: {region.relative_area * 100:.4f}% "
                                        f"(equals {region.absolute_area})")

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name=f"Relative region areas are plausible (larger than {area_threshold}% of whole page)",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_regions,
            error_polygons=[region.coordinates.exterior.coords for region in faulty_regions],
        )

    @CheckStatus.INFO.decorator
    def _region_check_intersection(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if there are no two regions that intersect each other.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_regions = []

        len_regions = len(self.regions)

        intersecting_regions = []
        for idx1 in range(len_regions):
            for idx2 in range(0, idx1, 1):
                if self.regions[idx1].coordinates.intersects(self.regions[idx2].coordinates):
                    faulty_regions += [self.regions[idx1], self.regions[idx2]]

                    try:
                        intersection = int(
                            self.regions[idx1].coordinates.intersection(self.regions[idx2].coordinates).area
                        )
                    except shapely.errors.GEOSException:
                        intersection = np.nan

                    intersecting_regions.append(
                        [
                            self.regions[idx1],
                            self.regions[idx2],
                            intersection
                         ]
                    )

        success = (len(faulty_regions) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following regions intersect each other:"
            verbose_description = error_description
            for region1, region2, intersection_area in intersecting_regions:
                error_description +=   f"\n            {region1}, {region2}"
                verbose_description += (f"\n            {region1}, {region2} "
                                        f"(Area of intersection: {intersection_area} px)")

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Regions do not intersect",
            error_description=error_description,
            erroneous_instances=faulty_regions,
            verbose_description=verbose_description,
        )


class LineChecks:
    """
    In class LineChecks, we collect the sanity checks that are related to regions.

    The checks are grouped into three classes:
        * CRITICAL: Those checks must never fail, as failure indicates severe errors.
        * WARNING: Failing these checks indicates errors, but there may be perfectly fine examples where the test fails.
        * INFO: Failing such tests occurs very often even in fine examples, so it is to be taken as additional
                information.
    If the check is passed (excluding INFO checks), CheckStatus.GOOD is returned.

    Attributes:
        lines (list[MainTextLine]): The list of main text lines the tests should be conducted on.
        regions (list[Region]): The list of regions the tests should be conducted on.

    Methods:
        check: Runs all checks and returns a list of CheckResult.

    Private Methods:
        _line_check_type: Check if the line type is a valid identifier. CRITICAL.
        _line_check_area: Check if the line area is larger than 0. CRITICAL.
        _line_check_text: Check if the line contains some text. CRITICAL.
        _line_check_numbering_zone: Check if the text lines in numbering zones consist of arabic numerals.
        _line_check_width: Check if the text line width is greater than 60% of the average text line width.
        _line_check_type_region_correspondence: Check that all lines are in the areas they belong to.
                                                 I.e., they should intersect with main regions only. WARNING.
        _line_check_region_intersection: Check that all lines intersect exactly one region each. INFO.
    """
    def __init__(self, page: METSPage):
        """
        Initialize a LineChecks instance.

        :param page: The METSPage on which the checks should be performed on.
        """
        self.lines = page.get_main_text_lines()
        self.regions = page.get_regions()

    def check(self) -> list[CheckResult]:
        """
        Performs the checks and returns the test results as a list of CheckResult.

        :return: Test results.
        """
        # Main text lines must be in main zone

        line_checks = [
            # CRITICAL
            self._line_check_type,
            self._line_check_area,
            self._line_check_text,
            self._line_check_numbering_zone,
            self._line_check_width,
            # WARNING
            self._line_check_type_region_correspondence,
            # INFO
            self._line_check_region_intersection,
        ]

        return [check_function() for check_function in line_checks]

    @CheckStatus.CRITICAL.decorator
    def _line_check_type(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the type of the line is a valid identifier.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_lines = []

        for line in self.lines:
            # check if the type is valid, i.e., a valid line type that is not for glosses
            if line.type not in MAIN_TEXT_LINE_TYPES:
                faulty_lines.append(line)

        success = (len(faulty_lines) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following lines have invalid line types:"
            verbose_description = error_description
            for line in faulty_lines:
                verbose_description += f"\n            {line} has invalid type '{line.type}'"
                verbose_description += f"\n            {line.to_minimal_string()} has invalid type '{line.type}'"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Main text line types are valid",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_lines,
            error_polygons=[line.coordinates.exterior.coords for line in faulty_lines],
        )

    @CheckStatus.CRITICAL.decorator
    def _line_check_area(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the area of the line is greater than 0.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_lines = []
        for line in self.lines:
            if line.coordinates.area < 1e-6:
                faulty_lines.append(line)

        success = (len(faulty_lines) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following lines encompass no area:"
            verbose_description = error_description
            for line in faulty_lines:
                error_description += f"\n            {line.to_minimal_string()} ({line.coordinates})"
                verbose_description += f"\n            {line}"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Main text line areas are greater than 0",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_lines,
            error_polygons=[line.baseline for line in faulty_lines],
        )

    @CheckStatus.CRITICAL.decorator
    def _line_check_text(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the line contains some text.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_lines = []
        for line in self.lines:
            if len(line.text) == 0:
                faulty_lines.append(line)

        success = (len(faulty_lines) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following lines contain no text:"
            verbose_description = error_description
            for line in faulty_lines:
                error_description += f"\n            {line.to_minimal_string()}"
                verbose_description += f"\n            {line}"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Main text lines contain some text",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_lines,
            error_polygons=[line.baseline for line in faulty_lines],
        )

    @CheckStatus.CRITICAL.decorator
    def _line_check_numbering_zone(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the text line in numbering zone contains arabic numerals.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        numbering_zones = []
        for region in self.regions:
            if region.type in (RegionType.NUMBERING_ZONE_PAGE, RegionType.NUMBERING_ZONE_FOLIO):
                numbering_zones.append(region)

        faulty_lines = []
        for line in self.lines:
            for region in numbering_zones:
                if line.coordinates.intersects(region.coordinates):
                    try:
                        int(line.text)
                    except ValueError:
                        faulty_lines.append(line)

        success = (len(faulty_lines) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following lines in numbering zones contain suspicious symbols:"
            verbose_description = error_description
            for line in faulty_lines:
                error_description += f"\n            {line.to_minimal_string()}"
                verbose_description += f"\n            {line}"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Text lines in numbering zones contain only arabic numerals",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_lines,
            error_polygons=[line.coordinates.exterior.coords for line in faulty_lines],
        )

    @CheckStatus.CRITICAL.decorator
    def _line_check_width(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the width of the text lines is greater than 60% the length of the average main text line.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """

        numbering_zones = []
        for region in self.regions:
            if region.type in (RegionType.NUMBERING_ZONE_PAGE, RegionType.NUMBERING_ZONE_FOLIO):
                numbering_zones.append(region)

        average_line_length = 0
        if len(self.lines) > 0:
            for line in self.lines:
                average_line_length += line.baseline[-1][0] - line.baseline[0][0]  # width of the line's baseline
            average_line_length /= len(self.lines)

        faulty_lines = []
        exceeding_percentages = []
        for line in self.lines:
            for region in numbering_zones:
                if not line.coordinates.intersects(region.coordinates):  # exclude numbering zone lines
                    text_line_length = line.baseline[-1][0] - line.baseline[0][0]
                    if text_line_length <= 0.6 * average_line_length:
                        faulty_lines.append(line)
                        exceeding_percentages.append(text_line_length / average_line_length)

        success = (len(faulty_lines) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following text line widths are suspiciously small (<= 60% of average main text line):"
            verbose_description = error_description
            for faulty_line, exceeding_percentage in zip(faulty_lines, exceeding_percentages):
                error_description += (f"\n            {faulty_line.to_minimal_string()} "
                                      f"({exceeding_percentage * 100:.2f}%)")
                verbose_description += (f"\n            {faulty_line} "
                                        f"({exceeding_percentage * 100:.2f}%)")

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Line widths are greater than 60% of average text line",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_lines,
            error_polygons=[gloss.coordinates.exterior.coords for gloss in faulty_lines],
        )

    @CheckStatus.WARNING.decorator
    def _line_check_type_region_correspondence(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the type of the line matches the region it is mainly intersecting.
        I.e., main text lines should be in main zones.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_lines = []

        expected_region = [  # text glosses should be in main region or numbering zone
                RegionType.MAIN_ZONE,
                RegionType.MAIN_ZONE_COLUMN_LEFT,
                RegionType.MAIN_ZONE_COLUMN_RIGHT,
                RegionType.NUMBERING_ZONE_PAGE,
                RegionType.NUMBERING_ZONE_FOLIO
            ]

        faulty_intersections = []
        for line in self.lines:
            current_areas = []
            for region in self.regions:
                try:
                    intersection_area = region.coordinates.intersection(line.coordinates).area
                except shapely.errors.GEOSException:
                    intersection_area = np.nan
                current_areas.append(intersection_area)
            argmax = np.argmax(current_areas)
            majority_region = self.regions[argmax]
            try:
                percentage = current_areas[argmax] / line.coordinates.area
            except ZeroDivisionError:
                percentage = np.nan

            if majority_region.type not in expected_region:
                faulty_lines.append(line)
                faulty_intersections.append([line, majority_region])

        success = (len(faulty_intersections) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following lines are largely outside their expected region:"
            verbose_description = f"Following lines are largely outside their expected region ({expected_region}):"
            for faulty_line, main_region in faulty_intersections:
                error_description += (f"\n            {faulty_line.to_minimal_string()}: {main_region.type} "
                                      f"({percentage*100:.2f}%)")
                verbose_description += (f"\n            {faulty_line} mainly is in {main_region} "
                                        f"({percentage*100:.2f}%)")

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Main text lines are inside their expected regions",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_lines,
            error_polygons=[line.coordinates.exterior.coords for line in faulty_lines],
        )

    @CheckStatus.INFO.decorator
    def _line_check_region_intersection(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the line intersects with exactly one region.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_lines = []

        faulty_intersections = []
        for line in self.lines:
            current_intersections = []
            current_areas = []
            for region in self.regions:
                if region.coordinates.intersects(line.coordinates):
                    current_intersections.append(region)
                    try:
                        current_areas.append(
                            region.coordinates.intersection(line.coordinates).area/line.coordinates.area
                        )
                    except shapely.errors.GEOSException:
                        current_areas.append(np.nan)
            if len(current_intersections) == 0 or len(current_intersections) > 1:
                faulty_lines.append(line)
                faulty_intersections.append([current_intersections, current_areas])

        success = (len(faulty_lines) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following lines intersect with none resp. more than one region:"
            verbose_description = error_description
            for faulty_line, faulty_intersection in zip(faulty_lines, faulty_intersections):
                # sort the regions according to the relative area descending
                sorted_regions = sorted(zip(faulty_intersection[0], faulty_intersection[1]),
                                        key=lambda x: x[1],
                                        reverse=True)
                error_description += (
                    f"\n            {faulty_line.to_minimal_string()} intersects "
                    f"{len(sorted_regions)} regions: "
                    f"{''.join([f'{region.type} ({area * 100:.1f}%), ' for region, area in sorted_regions])}"[:-2]
                )
                verbose_description += (
                    f"\n            {faulty_line} intersects "
                    f"{len(sorted_regions)} regions: "
                    f"{''.join([f'{region} ({area * 100:.1f}%), ' for region, area in sorted_regions])}"[:-2]
                )

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Main text lines intersect with exactly one region",
            error_description=error_description,
            erroneous_instances=faulty_lines,
            verbose_description=verbose_description,
        )


class GlossChecks:
    """
    In class GlossChecks, we collect the sanity checks that are related to regions.

    The checks are grouped into three classes:
        * CRITICAL: Those checks must never fail, as failure indicates severe errors.
        * WARNING: Failing these checks indicates errors, but there may be perfectly fine examples where the test fails.
        * INFO: Failing such tests occurs very often even in fine examples, so it is to be taken as additional
                information.
    If the check is passed (excluding INFO checks), CheckStatus.GOOD is returned.

    Attributes:
        glosses (list[GlossLine]): The list of glosses the tests should be conducted on.
        regions (list[Region]): The list of regions the tests should be conducted on.
        lines (list[MainTextLine]): The list of main text lines the tests should be conducted on.

    Methods:
        check: Runs all checks and returns a list of CheckResult.

    Private Methods:
        _gloss_check_type: Check if the gloss type is a valid identifier. CRITICAL.
        _gloss_check_area: Check if the gloss area is greater than zero. CRITICAL.
        _gloss_check_text: Check if the gloss contains some text. CRITICAL.
        _gloss_check_width: Check if the gloss width is less than 60% of the average text line. CRITICAL.
        _gloss_check_type_region_correspondence: Check that all glosses are in the areas they belong to.
                                                 E.g., marginal glosses should be in marginal zones. WARNING.
        _gloss_check_region_intersection: Check that all glosses intersect exactly one region each. INFO.
    """
    def __init__(self, page: METSPage):
        """
        Initialize a GlossChecks instance.

        :param page: The METSPage on which the checks should be performed on.
        """
        self.glosses = page.get_gloss_lines()
        self.regions = page.get_regions()
        self.lines = page.get_main_text_lines()

    def check(self) -> list[CheckResult]:
        """
        Performs the checks and returns the test results as a list of CheckResult.

        :return: Test results.
        """
        gloss_checks = [
            # CRITICAL
            self._gloss_check_type,
            self._gloss_check_area,
            self._gloss_check_text,
            self._gloss_check_width,
            # WARNING
            self._gloss_check_type_region_correspondence,
            # INFO
            self._gloss_check_region_intersection,
        ]

        return [check_function() for check_function in gloss_checks]

    @CheckStatus.CRITICAL.decorator
    def _gloss_check_type(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the type of the gloss is a valid identifier.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_glosses = []

        for gloss in self.glosses:
            # check if the type is valid, i.e., a valid line type but not default or title line
            if gloss.type not in dataclasses.astuple(LineType()) or gloss.type in [LineType.DEFAULT,
                                                                                   LineType.TITLE]:
                faulty_glosses.append(gloss)

        success = (len(faulty_glosses) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following glosses have invalid line types:"
            verbose_description = error_description
            for gloss in faulty_glosses:
                error_description += f"\n            {gloss.to_minimal_string()}  has invalid type '{gloss.type}'"
                verbose_description += f"\n            {gloss} has invalid type '{gloss.type}'"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Gloss types are valid",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_glosses,
            error_polygons=[gloss.coordinates.exterior.coords for gloss in faulty_glosses],
        )

    @CheckStatus.CRITICAL.decorator
    def _gloss_check_area(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the area of the gloss line is greater than 0.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_glosses = []
        for gloss in self.glosses:
            if gloss.coordinates.area < 1e-6:
                faulty_glosses.append(gloss)

        success = (len(faulty_glosses) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following glosses encompass no area:"
            verbose_description = error_description
            for gloss in faulty_glosses:
                error_description += f"\n            {gloss.to_minimal_string()}"
                verbose_description += f"\n            {gloss}"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Gloss line areas are greater than 0",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_glosses,
            error_polygons=[gloss.baseline for gloss in faulty_glosses],
        )

    @CheckStatus.CRITICAL.decorator
    def _gloss_check_text(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the gloss contains any text.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_glosses = []
        for gloss in self.glosses:
            if len(gloss.text) == 0:
                faulty_glosses.append(gloss)

        success = (len(faulty_glosses) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following glosses contain no text:"
            verbose_description = error_description
            for gloss in faulty_glosses:
                error_description += f"\n            {gloss.to_minimal_string()}"
                verbose_description += f"\n            {gloss}"

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Gloss line areas contain some text",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_glosses,
            error_polygons=[gloss.baseline for gloss in faulty_glosses],
        )

    @CheckStatus.CRITICAL.decorator
    def _gloss_check_width(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the width of the glosses is smaller than 60% the width of the average main text line.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        average_line_length = 0
        if len(self.lines) > 0:
            for line in self.lines:
                average_line_length += line.baseline[-1][0] - line.baseline[0][0]  # width of the line's baseline
            average_line_length /= len(self.lines)

        faulty_glosses = []
        exceeding_percentages = []
        for gloss in self.glosses:
            gloss_line_length = gloss.baseline[-1][0] - gloss.baseline[0][0]
            if gloss_line_length >= 0.6 * average_line_length:
                faulty_glosses.append(gloss)
                exceeding_percentages.append(gloss_line_length / average_line_length)

        success = (len(faulty_glosses) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following gloss widths are suspiciously large (>= 60% of average main text line):"
            verbose_description = error_description
            for faulty_gloss, exceeding_percentage in zip(faulty_glosses, exceeding_percentages):
                error_description += (f"\n            {faulty_gloss.to_minimal_string()} "
                                      f"({exceeding_percentage*100:.2f}%)")
                verbose_description += (f"\n            {faulty_gloss} "
                                        f"({exceeding_percentage*100:.2f}%)")

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Gloss widths are smaller than 60% of average text line",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_glosses,
            error_polygons=[gloss.coordinates.exterior.coords for gloss in faulty_glosses],
        )

    @CheckStatus.WARNING.decorator
    def _gloss_check_type_region_correspondence(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the type of the gloss matches the region it is mainly intersecting.
        E.g., marginal glosses should mainly be in marginal zones.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_glosses = []

        faulty_intersections = []
        for gloss in self.glosses:
            current_areas = []
            for region in self.regions:
                try:
                    intersection_area = region.coordinates.intersection(gloss.coordinates).area
                except shapely.errors.GEOSException:
                    intersection_area = np.nan
                current_areas.append(intersection_area)
            argmax = np.argmax(current_areas)
            majority_region = self.regions[argmax]
            try:
                percentage = current_areas[argmax] / gloss.coordinates.area
            except ZeroDivisionError:
                percentage = np.nan

            if "Interlinear" in gloss.type:  # interlinear glosses should be in main region
                expected_region = [
                    RegionType.MAIN_ZONE,
                    RegionType.MAIN_ZONE_COLUMN_LEFT,
                    RegionType.MAIN_ZONE_COLUMN_RIGHT
                ]
                if majority_region.type not in expected_region:
                    faulty_glosses.append(gloss)
                    faulty_intersections.append([gloss, majority_region, expected_region, percentage])
            elif "Intercolumnar" in gloss.type:  # intercolumnar glosses should be in intercolumnar region
                expected_region = RegionType.MAIN_ZONE_INTERCOLUMNAR
                if majority_region.type != expected_region:
                    faulty_glosses.append(gloss)
                    faulty_intersections.append([gloss, majority_region, expected_region, percentage])
            elif "Marginal" in gloss.type:  # marginal glosses should be in margins
                expected_region = [
                    RegionType.MARGIN_TEXT_ZONE_OUTER,
                    RegionType.MARGIN_TEXT_ZONE_INNER,
                    RegionType.MARGIN_TEXT_ZONE_UPPER,
                    RegionType.MARGIN_TEXT_ZONE_LOWER
                ]
                if majority_region.type not in expected_region:
                    faulty_glosses.append(gloss)
                    faulty_intersections.append([gloss, majority_region, expected_region, percentage])

        success = (len(faulty_intersections) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following glosses are largely outside their expected region:"
            verbose_description = error_description
            for faulty_gloss, main_region, expected_region, percentage in faulty_intersections:
                error_description += (f"\n            {faulty_gloss.to_minimal_string()} mainly in {main_region.type} "
                                      f"({percentage * 100:.2f}%)")
                verbose_description += (f"\n            {faulty_gloss} mainly in {main_region} "
                                        f"({percentage * 100:.2f}%)")

        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Glosses are inside their expected regions",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_glosses,
            error_polygons=[gloss.coordinates.exterior.coords for gloss in faulty_glosses],
        )

    @CheckStatus.INFO.decorator
    def _gloss_check_region_intersection(self, return_type: CheckStatus) -> CheckResult:
        """
        Check if the gloss intersects with exactly one region.

        :param return_type: The CheckStatus that is returned when the test has failed.
        :return: Individual test result.
        """
        faulty_glosses = []

        faulty_intersections = []
        for gloss in self.glosses:
            current_intersections = []
            current_areas = []
            for region in self.regions:
                if region.coordinates.intersects(gloss.coordinates):
                    current_intersections.append(region)
                    try:
                        current_areas.append(gloss.coordinates.intersection(region.coordinates).area/gloss.coordinates.area)
                    except shapely.errors.GEOSException:
                        current_areas.append(np.nan)
            if len(current_intersections) == 0 or len(current_intersections) > 1:
                faulty_glosses.append(gloss)
                faulty_intersections.append([current_intersections, current_areas])

        success = (len(faulty_glosses) == 0)

        error_description = ""
        verbose_description = ""
        if not success:
            error_description += f"Following glosses intersect with none resp. more than one region:"
            verbose_description = error_description
            for faulty_gloss, faulty_intersection in zip(faulty_glosses, faulty_intersections):
                # sort the regions according to the relative area descending
                sorted_regions = sorted(zip(faulty_intersection[0], faulty_intersection[1]),
                                        key=lambda x: x[1],
                                        reverse=True)
                error_description += (
                    f"\n            {faulty_gloss.to_minimal_string()} intersects "
                    f"{len(sorted_regions)} regions: "
                    f"{''.join([f'{region.type} ({area*100:.1f}%), 'for region, area in sorted_regions])}"[:-2]
                )
                verbose_description += (
                    f"\n            {faulty_gloss} intersects "
                    f"{len(sorted_regions)} regions: "
                    f"{''.join([f'{region} ({area * 100:.1f}%), ' for region, area in sorted_regions])}"[:-2]
                )
        return CheckResult(
            status=return_type if not success else CheckStatus.GOOD,
            name="Glosses intersect with exactly one region",
            error_description=error_description,
            verbose_description=verbose_description,
            erroneous_instances=faulty_glosses
        )
