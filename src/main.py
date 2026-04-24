import argparse
from bs4 import BeautifulSoup
import datetime
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as patches  # drawing polygons
import matplotlib.pyplot as plt
import numpy as np
import os
from textwrap import wrap  # automatic wrapping of text
import tqdm  # nice visualization of how long for loops will take

from connect_gui import start_gui
from glossit_connect_glosses import GlossOnPageConnector
from glossit_dataclasses import LineType, GlossLine, Word
from glossit_sanity_checks import CheckStatus, RegionChecks, LineChecks, GlossChecks
from xml_extraction import METSBook, apply_xslt_transformation


def apply_xslt(mets_path: str, xslt_path: str, output_file_path: str):
    """
    Given a METS XML file and an XSLT transformation, applies the transformation to the METS file and saves the
    transformation result to the location provided.

    :param mets_path: Path to the eScriptorium METS.
    :param xslt_path: Path to the GlossIT XSLT transformation.
    :param output_file_path: Path of the file the output is written to.
    :return:
    """
    # if no or an invalid file extension is found, add '.xml'
    extension = output_file_path.split(".")[-1]
    if extension.lower() != "xml":
        output_file_path += ".xml"

    transformed = apply_xslt_transformation(mets_path=os.path.abspath(mets_path), xslt_path=os.path.abspath(xslt_path))
    with open(output_file_path, "w") as file:
        file.write(str(transformed))
    print("DONE")


def sanity_check(
        mets_path: str,
        output_file_path: str = None,
        verbose: bool = False,
        display_info: bool = False,
        overwrite_pagexml: bool = False,
        region_checks: bool = True,
        line_checks: bool = True,
        gloss_checks: bool = True
):
    """
    Given a path to an eScriptorium METS output file, this function conducts
    some sanity checks for regions, main text lines and glosses. The checks performed encompass things such as that
    region names should be unique, marginal glosses should be in marginal zones, etc. The test results are then
    printed on the console and saved into a file.

    If region_checks, line_checks, and gloss_checks happen to be False at the same time, all checks are conducted.

    :param mets_path: Path to the eScriptorium METS.
    :param output_file_path: Path of the file the output is written to.
    :param verbose: Enables more detailed output.
    :param display_info: Enables the display of INFO checks.
    :param overwrite_pagexml: Overwrites the PageXML where faulty lines are annotated using the `sanity` attribute.
    :param region_checks: Conduct region checks.
    :param line_checks: Conduct main text line checks.
    :param gloss_checks: Conduct gloss line checks.
    :return:
    """

    # If all three are False, we conduct all tests by default
    if not (region_checks or line_checks or gloss_checks):
        region_checks = True
        line_checks = True
        gloss_checks = True

    pages = METSBook(mets_path=mets_path)  # , ocr_model_path=ocr_model_path)

    not_okay_types = (CheckStatus.CRITICAL, CheckStatus.WARNING)  # CheckStatus results that are treated as not ok

    console_lines = []  # for display on the console
    console_lines += [f"METS File: {mets_path}\n"]

    plain_lines = []  # for plain text output
    plain_lines += [f"METS File: {mets_path}\n"]

    errors_per_page = []
    collected_errors = []
    print("\nConducting checks:")
    for idx, page in tqdm.tqdm(enumerate(pages.pages)):
        page_string = f"PAGE {idx+1} ({os.path.basename(page.pagexml_path)}, {os.path.basename(page.image_path)})"

        console_lines += [f"\n{page_string}"]
        plain_lines += [page_string]

        # PDF report display, only append suspicious types for readability
        filtered_region_checks = []
        filtered_line_checks = []
        filtered_gloss_checks = []

        if region_checks:
            region_check_results = RegionChecks(page).check()

            # console output
            console_lines += ["  Region checks:"]
            console_lines += [result.to_console_string(verbose_output=verbose) for result in
                              region_check_results]
            console_lines.append("")
            # plain text output
            plain_lines += ["  Region checks:"]
            plain_lines += [result.to_plain_string(verbose_output=verbose) for result in
                            region_check_results]
            plain_lines.append("")

            filtered_region_checks = [check for check in region_check_results if check.status in not_okay_types]
        if line_checks:
            line_check_results = LineChecks(page).check()

            # console output
            console_lines.append("  Line checks:")
            console_lines += [result.to_console_string(verbose_output=verbose) for result in
                              line_check_results]
            console_lines.append("")
            # plain text output
            plain_lines.append("  Line checks:")
            plain_lines += [result.to_plain_string(verbose_output=verbose) for result in
                            line_check_results]
            plain_lines.append("")

            filtered_line_checks = [check for check in line_check_results if check.status in not_okay_types]
        if gloss_checks:
            gloss_check_results = GlossChecks(page).check()

            # console output
            console_lines.append("  Gloss checks:")
            console_lines += [result.to_console_string(verbose_output=verbose) for result in
                              gloss_check_results]
            # plain text output
            plain_lines.append("  Gloss checks:")
            plain_lines += [result.to_plain_string(verbose_output=verbose) for result in
                            gloss_check_results]
            plain_lines.append("\n\n")

            filtered_gloss_checks = [check for check in gloss_check_results if check.status in not_okay_types]

        combined_filtered_checks = filtered_region_checks + filtered_line_checks + filtered_gloss_checks
        collected_errors.append(combined_filtered_checks)

        for result in combined_filtered_checks:
            errors_per_page.append((page_string, page.pageimg, result))

    for line in console_lines:
        if verbose or display_info or "INFO" not in line:  # filter out INFO for non-verbose output
            print(line)
    print("\n")

    if overwrite_pagexml:
        print("\nOverwriting PageXML with error annotations:")

        for page, page_errors in tqdm.tqdm(zip(pages, collected_errors)):
            id_error_dict = {}
            # Collect the errors for each line and assign the line the highest occurring error priority
            for error in page_errors:
                for instance in error.erroneous_instances:
                    if instance.id not in id_error_dict:  # if the line is not marked yet, add the CheckStatus
                        id_error_dict[instance.id] = error.status.get_string().lower()
                    else:  # otherwise, we must ensure that a critical error is not overwritten by a warning!
                        if error.status == CheckStatus.CRITICAL:
                            id_error_dict[instance.id] = CheckStatus.CRITICAL.get_string().lower()

            # Annotate it in the PageXML
            pagexml = None
            with open(page.pagexml_path, "r") as file:
                pagexml = BeautifulSoup(file, features="xml")

                # we need to set a rendition so that a framework can operate
                # and display the error classes correctly
                pcgts_tag = pagexml.find("PcGts")
                pcgts_tag["rendition"] = "glossit_typing"

                # If necessary, delete old error tags from the METS
                sanity_tags = pagexml.find_all(lambda tag: tag.get("sanity") is not None)
                for tag in sanity_tags:
                    tag.attrs = {key: value for key, value in tag.attrs.items() if key != "sanity"}

                # Add the sanity tags according to the status of each line
                for id, status in id_error_dict.items():
                    affected_tag = pagexml.find(lambda tag: tag.get("id") == id)
                    affected_tag["sanity"] = status

            # Overwrite PageXML
            if pagexml is not None:
                with open(page.pagexml_path, "w") as file:
                    file.write(str(pagexml))

    if output_file_path is not None:
        with open(output_file_path + ".txt", "w") as file_handle:
            for line in plain_lines:
                if verbose or display_info or "INFO" not in line:  # filter out INFO for non-verbose output
                    file_handle.write(line + "\n")

        print("\nConstructing PDF output:")
        with PdfPages(output_file_path + ".pdf") as pdf:
            plt.rcParams["text.usetex"] = False
            plt.rcParams['font.family'] = 'Junicode'

            for page_string, page_img, error in tqdm.tqdm(errors_per_page):
                plt.figure()
                plt.gca().axis("off")
                plt.title(f"GlossIT METS Sanity Check of {mets_path}\n" + "\n".join(wrap(f"{page_string}: {error.name}")))
                plt.imshow(np.asarray(page_img)//2)
                pdf.attach_note(f"{page_string}: {error.name}")  # attach metadata (as pdf note) to page
                plt.figtext(0.05, 0, error.to_plain_string(), ha="left", va="top")

                if error.status == CheckStatus.CRITICAL:
                    color = "#FF0000A0"
                elif error.status == CheckStatus.WARNING:
                    color = "#FFFF00A0"
                else:
                    color = "#00FF00A0"

                for polygon in error.error_polygons:
                    rect = patches.Polygon(polygon, linewidth=1, edgecolor=color, facecolor="none")
                    plt.gca().add_patch(rect)

                pdf.savefig(bbox_inches = "tight")
                plt.close()

            d = pdf.infodict()
            d["Title"] = f"GlossIT METS Sanity Check of {mets_path}"
            d["Author"] = "Tristan Repolusk"
            d["CreationDate"] = datetime.datetime.today()
            d["ModDate"] = d["CreationDate"]
    print("DONE")


def connect_glosses(mets_path: str, tei_path: str, ocr_model_path: str, output_file_path: str):
    """
    Given a path to an eScriptorium METS output file and the path to the GlossIT TEI
    XSLT transformation, this function attempts an automatic connection of glosses.

    :param mets_path: Path to the eScriptorium METS.
    :param tei_path: Path to the GlossIT TEI file (obtained by applying the first transformation on the METS XML).
    :param ocr_model_path: Path to Kraken OCR model.
    :param output_file_path: Path of the file the output is written to.
    :return:
    """

    pages = METSBook(mets_path=mets_path, tei_path=tei_path, ocr_model_path=ocr_model_path, verbose=True)

    global_connections: list[GlossOnPageConnector] = []

    print("\nConnecting glosses on each page:")
    for idx, page in tqdm.tqdm(enumerate(pages.pages)):
        global_connections.append(GlossOnPageConnector(page))

    def get_gloss_color(gloss: GlossLine):
        if gloss.type == LineType.REFERENCE_SIGN:
            return "#0000FF30"  # blue
        else:
            return "#00FF0030"  # green

    print("\nConstructing PDF output:")
    with PdfPages(output_file_path + ".pdf") as pdf:
        plt.rcParams["text.usetex"] = False
        plt.rcParams['font.family'] = 'Junicode'

        for idx, page_connector in tqdm.tqdm(enumerate(global_connections)):
            page_connections = page_connector.connections
            page_connection_cycles = page_connector.connection_chains
            if len(page_connections) == 0:  # if we have no connections on a page, there's nothing left to do
                continue

            current_page = page_connections[0].start.page
            page_img = current_page.pageimg
            page_string = (f"PAGE {idx + 1} ({os.path.basename(current_page.pagexml_path)}, "
                           f"{os.path.basename(current_page.image_path)})")

            plt.figure(figsize=(20, 30))
            plt.gca().axis("off")
            plt.imshow(current_page.pageimg)

            plt.title(f"GlossIT METS Connect Glosses of {mets_path} ({tei_path})\n" + "\n".join(wrap(f"{page_string}")),
                      fontsize=30)
            plt.imshow(np.asarray(page_img))
            pdf.attach_note(f"{page_string}")  # attach metadata (as pdf note) to page

            connection_string = ""
            for cycle in page_connection_cycles:
                for entry in cycle:
                    connection_string += f"{entry.start.to_minimal_string()} → "
                connection_string += f"{cycle[-1].end}"
                connection_string += "\n"
            plt.figtext(0.05, 0, connection_string, ha="left", va="top", fontsize=30)

            for connection in page_connections:
                red = "#FF000030"
                assert (
                    isinstance(connection.start, GlossLine))  # starting point from a connection must always be a gloss
                assert (isinstance(connection.end, (Word, GlossLine)))

                color = get_gloss_color(connection.start)
                rect = patches.Polygon(connection.start.coordinates.exterior.coords, linewidth=1, edgecolor=color,
                                       facecolor=color)
                plt.gca().add_patch(rect)

                start_center = np.mean(connection.start.baseline, axis=0)

                if isinstance(connection.end, Word):
                    rect = patches.Polygon(connection.end.bounding_box, linewidth=1, edgecolor=red, facecolor=red)
                    end_center = np.mean(connection.end.bounding_box, axis=0)
                else:  # connection.end must be gloss in this case
                    color = get_gloss_color(connection.end)
                    rect = patches.Polygon(connection.end.coordinates.exterior.coords, linewidth=1, edgecolor=color,
                                           facecolor=color)
                    end_center = np.mean(connection.end.baseline, axis=0)
                plt.gca().add_patch(rect)
                plt.gca().annotate("", xytext=start_center, xy=end_center,
                                   arrowprops=dict(arrowstyle="-|>", mutation_scale=20, color="k"))

            pdf.savefig(bbox_inches = "tight")
            plt.close()

        d = pdf.infodict()
        d["Title"] = f"GlossIT METS Sanity Check of {mets_path}"
        d["Author"] = "Tristan Repolusk"
        d["CreationDate"] = datetime.datetime.today()
        d["ModDate"] = d["CreationDate"]
    print("DONE")


def bulk_split_mets(input_folder: str):
    """
    Given an XSLT transformation and a folder containing
    a complete METS.xml, it splits the METS into smaller single-page METS
    for each manuscript page. These are then saved as `*_METS.xml`. Note that
    each PageXML and image JPG must have the same name except for the file extension!
    E.g., 181_5da43_default.xml and 181_5da43_default.jpg.
    :param input_folder: Path to the folder containing the METS.xml.
    """

    from bs4 import BeautifulSoup
    import os
    from tqdm import tqdm

    from xml_extraction import METSBook

    def construct_mets(image_names: list[str], xml_names: list[str]) -> BeautifulSoup:
        """
        Constructs a new METSFile from a list of image names and PageXML names.
        Note that image_names[0] corresponds to xml_names[0] and so forth.
        :param image_names: List of image names.
        :param xml_names: List of XML names.
        :return: BeautifulSoup of a METS.xml linking the image_names and xml_names.
        """

        assert(len(image_names) == len(xml_names))

        # 1) Construct fileSec
        fileGrp_image = '<fileGrp USE="image">'
        for page_idx, image_name in enumerate(image_names):
            fileGrp_image += f'<file ID="image{page_idx}">'
            fileGrp_image += f'<FLocat xlink:href="{image_name}"/>'
            fileGrp_image += '</file>'
        fileGrp_image += '</fileGrp>'

        fileGrp_export = '<fileGrp USE="export">'
        for page_idx, xml_name in enumerate(xml_names):
            fileGrp_export += f'<file ID="export{page_idx}">'
            fileGrp_export += f'<FLocat xlink:href="{xml_name}"/>'
            fileGrp_export += '</file>'
        fileGrp_export += '</fileGrp>'

        fileSec = f'{fileGrp_image}{fileGrp_export}'

        # 2) Construct structMap
        structMap = '<div TYPE="document">'
        for page_idx, _ in enumerate(xml_names):
            structMap += f'<div TYPE="page">'
            structMap += f'<fptr FILEID="image{page_idx}"/>'
            structMap += f'<fptr FILEID="export{page_idx}"/>'
            structMap += '</div>'
        structMap += '</div>'

        # 3) Merge data
        mets_string = '<mets xmlns="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink">'
        mets_string += f'<fileSec>{fileSec}</fileSec>'
        mets_string += f'<structMap TYPE="physical">{structMap}</structMap>'
        mets_string += '</mets>'

        return BeautifulSoup(mets_string, features="xml")

    print(f"\nAutomatically splitting the large METS.xml into smaller single-page *_METS.xml in {input_folder}:\n")

    image_names = []
    xml_names = []
    print("\n\nStep 1: Collecting METS data")
    for page in tqdm(METSBook(os.path.join(input_folder, "METS.xml"))):
        image_relpath = os.path.relpath(input_folder, os.path.dirname(page.image_path))
        image_name = os.path.join(
            image_relpath,
            os.path.basename(page.image_path)
        ) if image_relpath != "." else os.path.basename(page.image_path)
        image_names.append(image_name)

        xml_relpath = os.path.relpath(input_folder, os.path.dirname(page.pagexml_path))
        xml_name = os.path.join(
            xml_relpath,
            os.path.basename(page.pagexml_path)
        ) if xml_relpath != "." else os.path.basename(page.pagexml_path)
        xml_names.append(xml_name)

    print("\n\nStep 2: Writing to file system")
    for image_name, xml_name in tqdm(zip(image_names, xml_names)):
        mets_filename = os.path.join(input_folder, f"{xml_name.split(".")[0]}_METS.xml")
        mets_content = construct_mets([image_name], [xml_name])

        with open(mets_filename, "w") as file_handle:
            file_handle.write(str(mets_content))


def bulk_apply_xslt(input_folder: str, xslt_path: str):
    """
    Given an XSLT transformation and a folder containing
    <name>_METS.xml, it applies the XSLT transformation to each
    METS file and saving the result as <name>_TEI.xml
    inside the input folder.
    :param input_folder: Path to the folder containing the <name>_METS.xml.
    :param xslt_path: Path to the XSLT transformation file.
    """

    import os
    from tqdm import tqdm

    print(f"\nAutomatically creating *_TEI.xml for each *_METS.xml in {input_folder}:\n")

    page_names = [file.split(".")[0] for file in os.listdir(input_folder) if
                  "METS" not in file and "TEI" not in file and file.split(".")[-1] == "xml"]

    for page_name in tqdm(page_names):
        mets_filename = os.path.join(input_folder, f"{page_name}_METS.xml")
        tei_filename = os.path.join(input_folder, f"{page_name}_TEI.xml")

        tei_content = apply_xslt_transformation(os.path.abspath(mets_filename),
                                                os.path.abspath(xslt_path))

        with open(tei_filename, "w") as file_handle:
            file_handle.write(str(tei_content))


def bulk_create_glp(input_folder: str, ocr_model: str):
    """
    Given a kraken recognition model, scans the folder input_folder for files of the names
    <name>_METS.xml and <name>_TEI.xml and outputs a GLP project file <name>.glp in the input_folder.
    :param input_folder: Path to the folder containing the <name>_METS.xml and <name>_TEI.xml.
    :param ocr_model: Path to the Kraken recognition *.mlmodel file.
    """

    import os
    from tqdm import tqdm
    import umsgpack
    import zlib

    from xml_extraction import METSBook
    from gui_files.gloss_connector_manager import ObservableGlossOnPageConnector
    from gui_files.program_state import ProgramStateSingleton

    print(f"\nAutomatically creating GLP files for the folder {input_folder}:\n")

    mets_names = sorted([file.split("_METS.xml")[0] for file in os.listdir(input_folder) if "_METS.xml" in file])
    tei_names = sorted([file.split("_TEI.xml")[0] for file in os.listdir(input_folder) if "_TEI.xml" in file])

    assert(mets_names == tei_names)

    program_state = ProgramStateSingleton().program_state

    for page_name in tqdm(mets_names):
        program_state.reset()

        mets_filename = os.path.abspath(os.path.join(input_folder, f"{page_name}_METS.xml"))
        tei_filename = os.path.abspath(os.path.join(input_folder, f"{page_name}_TEI.xml"))
        save_filename = os.path.abspath(os.path.join(input_folder, f"{page_name}.glp"))

        ocr_filename = os.path.abspath(ocr_model)

        program_state.path_to_mets = mets_filename
        program_state.path_to_tei = tei_filename
        program_state.path_to_model = ocr_filename

        program_state.mets_book = METSBook(
            mets_path=program_state.path_to_mets,
            tei_path=program_state.path_to_tei,
            ocr_model_path=program_state.path_to_model
        )

        connections = []
        for page in program_state.mets_book:
            connections.append(ObservableGlossOnPageConnector(page))
        program_state.gloss_connection_handler.connector_list = connections

        save_file = program_state.to_dict(tqdm_progress=None)
        serialized_data = umsgpack.dumps(save_file)
        compressed_data = zlib.compress(serialized_data)

        with open(save_filename, "wb") as file:
            file.write(compressed_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XML Tools for the GlossIT project.")

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # apply XSLT
    parser_mode_xslt = subparsers.add_parser("xslt", help="Apply XSLT transformation to METS XML file")
    parser_mode_xslt.add_argument("--mets", type=str, required=True, help="Path to METS file")
    parser_mode_xslt.add_argument("--xslt", type=str, required=True,
                                   help="Path to GlossIT TEI XSLT transformation file")
    parser_mode_xslt.add_argument("--output-file", type=str, required=True,
                                    help="Path to the file to which the transformed output should be saved.")

    # sanity checks
    parser_mode_sanity = subparsers.add_parser("sanity", help="Sanity checks for eScriptorium METS output files")
    parser_mode_sanity.add_argument("--mets", type=str, required=True, help="Path to METS file")
    parser_mode_sanity.add_argument("--output-file", type=str, required=False,
                                    help="Path to the file to which the sanity check output should be saved. "
                                   "If not provided, no file is saved")
    parser_mode_sanity.add_argument("--verbose", action="store_true", help="Enable verbose output "
                                                                     "(includes verbose INFO output)")
    parser_mode_sanity.add_argument("--info", action="store_true", help="Enable INFO output")
    parser_mode_sanity.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrites PageXML files with an additional 'sanity' tag in the suspicious regions/lines"
    )
    parser_mode_sanity.add_argument("--region", action="store_true", help="Conduct region checks")
    parser_mode_sanity.add_argument("--line", action="store_true", help="Conduct main text line checks")
    parser_mode_sanity.add_argument("--gloss", action="store_true", help="Conduct gloss line checks")

    # automatically connect glosses
    parser_mode_gloss = subparsers.add_parser("auto-gloss", help="Automatically connect glosses")
    parser_mode_gloss.add_argument("--mets", type=str, required=True, help="Path to METS file")
    parser_mode_gloss.add_argument("--tei", type=str, required=True,
                                   help="Path to GlossIT TEI file (typically obtained by applying the "
                                        "first XSLT transformation to the METS file)")
    parser_mode_gloss.add_argument("--ocr-model", type=str, required=True,
                                   help="Path to Kraken OCR model")
    parser_mode_gloss.add_argument("--output-file", type=str, required=True,
                                   help="Path to the output XML file, containing the connected glosses")

    # start the GlossIT Gloss Connector GUI
    parser_mode_gloss = subparsers.add_parser("gloss-connector", help="Start the GlossIT Gloss Connector GUI")

    # bulk split METS
    parser_mode_bulk_split_mets = subparsers.add_parser("bulk-split-mets",
                                                        help="Splits the METS file METS.xml into single-page XML files"
                                                             "of the naming schema *_METS.xml into the input folder.")
    parser_mode_bulk_split_mets.add_argument("--input-folder", type=str, required=True,
                                             help="Folder that contains a manuscript METS.xml")

    # bulk application of XSLT
    parser_mode_bulk_apply_xslt = subparsers.add_parser("bulk-apply-xslt",
                                                   help="Given an XSLT transformation and a folder containing"
                                                        "<name>_METS.xml, it applies the XSLT transformation to each"
                                                        "METS file and saving the result as <name>_TEI.xml"
                                                        "inside the input folder.")
    parser_mode_bulk_apply_xslt.add_argument("--input-folder", type=str, required=True,
                                        help="Folder that contains *_METS.xml")
    parser_mode_bulk_apply_xslt.add_argument("--xslt", type=str, required=True,
                                  help="Path to GlossIT TEI XSLT transformation file")

    # bulk creation of GLP
    parser_mode_bulk_create_glp = subparsers.add_parser("bulk-create-glp",
                                                        help="Given a folder containing <name>_METS.xml and <name>_TEI.xml,"
                                                        "creates a valid GlossIT Gloss Connector GLP file with the name"
                                                        "<name>.glp inside the folder.")
    parser_mode_bulk_create_glp.add_argument("--input-folder", type=str, required=True,
                                             help="Folder that contains *_METS.xml and *_TEI.xml")
    parser_mode_bulk_create_glp.add_argument("--ocr-model", type=str, required=True,
                                             help="Path to Kraken OCR model")

    args = parser.parse_args()

    # dispatch based on mode
    if args.mode == "xslt":
        print("\n*APPLY XSLT TRANSFORMATION*\n\n")
        apply_xslt(
            mets_path=args.mets,
            xslt_path=args.xslt,
            output_file_path=args.output_file
        )
    elif args.mode == "sanity":
        print("\n*METS SANITY CHECK*\n\n")
        sanity_check(
            mets_path=args.mets,
            output_file_path=args.output_file,
            verbose=args.verbose,
            display_info=args.info,
            overwrite_pagexml=args.overwrite,
            region_checks=args.region,
            line_checks=args.line,
            gloss_checks=args.gloss
        )
    elif args.mode == "auto-gloss":
        print("\n*METS CONNECT GLOSSES*\n\n")
        connect_glosses(
            mets_path=args.mets,
            tei_path=args.tei,
            ocr_model_path=args.ocr_model,
            output_file_path=args.output_file
        )
    elif args.mode == "gloss-connector":
        start_gui()
    elif args.mode == "bulk-split-mets":
        bulk_split_mets(
            input_folder=args.input_folder,
        )
    elif args.mode == "bulk-apply-xslt":
        bulk_apply_xslt(
            input_folder=args.input_folder,
            xslt_path=args.xslt
        )
    elif args.mode == "bulk-create-glp":
        bulk_create_glp(
            input_folder=args.input_folder,
            ocr_model=args.ocr_model
        )



