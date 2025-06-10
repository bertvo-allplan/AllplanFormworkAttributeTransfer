"""
Assign Object Attributes to Rebar
v1.0 - created on 10/06/2025 by Bert Van Overmeir.
"""

from typing import Any, List, TYPE_CHECKING, cast
from enum import Enum

import NemAll_Python_IFW_ElementAdapter as AllplanElementAdapter
import NemAll_Python_Geometry as AllplanGeometry
import NemAll_Python_IFW_Input as AllplanIFW
import NemAll_Python_BaseElements as AllplanBaseElements
import NemAll_Python_Utility as AllplanUtil
import Utils as Utils
import BuildingElementStringTable as BuildingElementStringTable
import AnyValueByType as AnyValueByType

from BuildingElement import BuildingElement
from BuildingElementComposite import BuildingElementComposite
from BuildingElementPaletteService import BuildingElementPaletteService
from StringTableService import StringTableService
from ControlProperties import ControlProperties
from BuildingElementListService import BuildingElementListService
from CreateElementResult import CreateElementResult
import Utils.LibraryBitmapPreview
from BuildingElementAttributeList import BuildingElementAttributeList
from ControlPropertiesUtil import ControlPropertiesUtil


def create_preview(_build_ele: BuildingElement,
                   _doc      : AllplanElementAdapter.DocumentAdapter) -> CreateElementResult:
    """ Creation of the element preview

    Args:
        _build_ele: building element with the parameter properties
        _doc:       document of the Allplan drawing files

    Returns:
        created elements for the preview
    """

    return CreateElementResult(Utils.LibraryBitmapPreview.create_library_bitmap_preview(r"C:\Users\bovermeir\Documents\Nemetschek\Allplan\2025\Usr\Local\Library\BendingMachineWizard\bending.png"))

def check_allplan_version(build_ele, version):
    return True

def create_interactor(coord_input:               AllplanIFW.CoordinateInput,
                      pyp_path:                  str,
                      _global_str_table_service: StringTableService,
                      build_ele_list:            List[BuildingElement],
                      build_ele_composite:       BuildingElementComposite,
                      control_props_list:        List[ControlProperties],
                      modify_uuid_list:          list):
    interactor = AssignAttributesInteractor(coord_input, pyp_path, build_ele_list, build_ele_composite,
                                         control_props_list, modify_uuid_list)
    return interactor


class Event(Enum):
    NO_EVENT = 0
    OBJECT_SELECTION = 1
    OBJECT_CALCULATION = 2


class EventOrigin(Enum):
    BUTTONCLICK = 0
    SELECTIONCOMPLETE_SINGLE = 1
    SELECTIONCOMPLETE_MULTI = 2
    SELECTIONCOMPLETE_POINT = 3
    OTHER = 4


class ApplicationStates(Enum):
    INFO_IDLE = 0
    INFO_SELECTION = 1
    ERROR_NO_GEOMETRY_SELECTED = 2
    ERROR_NO_REINFORCEMENT_SELECTED = 3
    ERROR_NOTHING_SELECTED = 4
    ERROR_PARAMETERS_NOT_SET = 5
    ERROR_TRANSFERRING_ATTRIBUTES = 6
    ERROR_READING_ATTRIBUTES = 7
    INFO_FINISHED = 8
    ERROR_UNSUPPORTED_REBAR_SHAPE = 9


class SelectionType(Enum):
    NONE = 0
    SINGLE_SELECTION = 1
    MULTISELECTION = 2
    FACE_SELECTION = 3
    INPUT_POINT = 4


class AssignAttributesInteractor():
    """
    Definition of class AssignAttributesInteractor
    """
    def __init__(self,
                 coord_input:           AllplanIFW.CoordinateInput,
                 pyp_path:              str,
                 build_ele_list:        List[BuildingElement],
                 build_ele_composite:   BuildingElementComposite,
                 control_props_list:    List[ControlProperties],
                 modify_uuid_list:      list):
        """
        Create the interactor

        Args:
            coord_input:               coordinate input
            pyp_path:                  path of the pyp file
            build_ele_list:            building element list
            build_ele_composite:       building element composite
            control_props_list:        control properties list
            modify_uuid_list:          UUIDs of the existing elements in the modification mode
        """

        self.coord_input         = coord_input
        self.pyp_path            = pyp_path
        self.build_ele_list      = build_ele_list
        self.build_ele_composite = build_ele_composite
        self.control_props_list  = control_props_list
        self.modify_uuid_list    = modify_uuid_list
        self.palette_service     = None
        self.model_ele_list      = []
        self.modification        = False
        self.close_interactor    = False
        self.user_origin_event   = Event.NO_EVENT
        self.user_selection_mode = SelectionType.NONE
        self.user_selection      = AllplanIFW.PostElementSelection()
        self.user_mulitselection_list = None
        self.user_referencepoints= []
        self.user_single_selection_list     = AllplanElementAdapter.BaseElementAdapter()
        self.user_filter         = None
        self.user_message        = ""
        self.is_second_input_point = False
        self.ctrl_prop_util      = None
        # start palette VIS
        self.palette_service = BuildingElementPaletteService(self.build_ele_list, self.build_ele_composite,
                                                             self.build_ele_list[0].script_name,
                                                             self.control_props_list, pyp_path + "\\")
        self.palette_service.show_palette(self.build_ele_list[0].pyp_file_name)
        (local_str_table, global_str_table) = self.build_ele_list[0].get_string_tables()
        self.ctrl_prop_util = ControlPropertiesUtil(control_props_list, build_ele_list)
        # workaround "list may not be empty upon visibility change" BUG
        temp_list = self.build_ele_list[0].AttributeIDFilter.value
        if 0 not in temp_list:
            temp_list.append(0)
        # set startup vis
        AllplanHelpers.static_init(self.coord_input, local_str_table)
        AllplanHelpers.show_message_in_taskbar(AllplanHelpers.get_message(ApplicationStates.INFO_IDLE))
        # init variables
        self.attribute_settings = None

    def on_control_event(self, event_id):
        """ control the different ID's that can be called via buttons.
        """
        self.palette_service.on_control_event(event_id)
        self.palette_service.update_palette(-1, True)
        self.set_event(Event(event_id))
        self.event_do(EventOrigin.BUTTONCLICK)

    def disable_variable_function(self) -> bool:
        return False

    def enable_variable_function(self) -> bool:
        return True

    def process_mouse_msg(self, mouse_msg, pnt, msg_info):
        """
        Process user input depending on the defined selection mode by the program (SelectionType.xxx).<br>
        After the action is completed, the user will be directed towards the defined user_origin_event with flag EventOrigin.[SelectionType].<br>
        User input data is saved in user_single_selection_list, user_multiselection_list or user_referencepoints depending on SelectionType.
        """
        if self.get_selection_mode() == SelectionType.SINGLE_SELECTION:
            is_element_found = self.coord_input.SelectElement(mouse_msg,pnt,msg_info,True,True,True)
            if is_element_found:
                self.user_single_selection_list = self.coord_input.GetSelectedElement()
                self.event_do(EventOrigin.SELECTIONCOMPLETE_SINGLE)
                return True

        if self.get_selection_mode() == SelectionType.MULTISELECTION:
            self.user_mulitselection_list = self.user_selection.GetSelectedElements(self.coord_input.GetInputViewDocument())
            if len(self.user_mulitselection_list) == 0:
                self.start_selection(SelectionType.MULTISELECTION, self.user_filter, self.user_message)
                return True
            else:
                self.event_do(EventOrigin.SELECTIONCOMPLETE_MULTI)
                return True

        if self.get_selection_mode() == SelectionType.INPUT_POINT:
            input_pnt = self.coord_input.GetInputPoint(mouse_msg, pnt, msg_info)

        if not self.coord_input.IsMouseMove(mouse_msg) and self.get_selection_mode() == SelectionType.INPUT_POINT:
            self.user_referencepoints.append(input_pnt.GetPoint())
            self.event_do(EventOrigin.SELECTIONCOMPLETE_POINT)
            return True

        if self.coord_input.IsMouseMove(mouse_msg):
            return True
        return True

    def start_selection(self,
                        selection_type: SelectionType,
                        filter        : AllplanIFW.SelectionQuery,
                        user_message  : str):
        """ start the selection process defined by a few variables

        Args:
            selection_type: The required selection type, either single, multi or point select.<br>
            filter:         An optional filter to be defined in the selection. Warning: Filter can be overridden in Allplan by user.<br>
            user_message:   Bottom left message to show in Allplan while selecting.
        """
        self.user_filter = filter
        self.user_message = user_message
        self.set_selection_mode(selection_type)

        if selection_type == SelectionType.SINGLE_SELECTION:
            prompt_msg = AllplanIFW.InputStringConvert(user_message)
            self.coord_input.InitFirstElementInput(prompt_msg)

        if filter:
            ele_select_filter = AllplanIFW.ElementSelectFilterSetting(filter,bSnoopAllElements = False)
            self.coord_input.SetElementFilter(ele_select_filter)

        if selection_type == SelectionType.MULTISELECTION:
            AllplanIFW.InputFunctionStarter.StartElementSelect(user_message,ele_select_filter,self.user_selection,markSelectedElements = True)

        if selection_type == SelectionType.INPUT_POINT:
            input_mode = AllplanIFW.CoordinateInputMode(
            identMode       = AllplanIFW.eIdentificationMode.eIDENT_POINT,
            drawPointSymbol = AllplanIFW.eDrawElementIdentPointSymbols.eDRAW_IDENT_ELEMENT_POINT_SYMBOL_YES)
            prompt_msg = AllplanIFW.InputStringConvert(user_message)
            if not self.is_second_input_point:
                self.coord_input.InitFirstPointInput(prompt_msg, input_mode)
                self.is_second_input_point = True
            else:
                self.coord_input.InitNextPointInput(prompt_msg,input_mode)
                self.is_second_input_point = False
        if selection_type == SelectionType.NONE:
            self.coord_input.InitFirstElementInput(AllplanIFW.InputStringConvert("Execute by button click"))

        return

    def event_do(self, event_origin: EventOrigin):
        self.set_selection_mode(SelectionType.NONE)
        if self.get_event() == Event.NO_EVENT:
            return False

        if self.get_event() == Event.OBJECT_SELECTION:
            if event_origin == EventOrigin.BUTTONCLICK:
                # get user preferences
                AllplanHelpers.log("[FormworkToRebarAttributes]","Getting user preferences",False)
                ok, self.attribute_settings = AllplanHelpers.get_user_attribute_settings(self.build_ele_list[0])
                if(not ok):
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_PARAMETERS_NOT_SET), AllplanUtil.MB_OK)
                    return False
                # lock user interface
                self.lock_user_interface(True)
                # select the elements to copy to other drawing files
                AllplanHelpers.log("[FormworkToRebarAttributes]","Setting filter and start selection",False)
                filter = self.create_filter([AllplanElementAdapter.Slab_TypeUUID, AllplanElementAdapter.Column_TypeUUID,
                                             AllplanElementAdapter.Beam_TypeUUID, AllplanElementAdapter.WallTier_TypeUUID,
                                             AllplanElementAdapter.Volume3D_TypeUUID, AllplanElementAdapter.BRep3D_Volume_TypeUUID,
                                             AllplanElementAdapter.Cylinder3D_TypeUUID, AllplanElementAdapter.Sphere3D_TypeUUID,
                                             AllplanElementAdapter.BarsLinearPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsLinearMultiPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsAreaPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsSpiralPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsCircularPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsRotationalSolidPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsRotationalPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsTangentionalPlacement_TypeUUID,
                                            AllplanElementAdapter.BarsEndBendingPlacement_TypeUUID])
                self.start_selection(SelectionType.MULTISELECTION, filter , AllplanHelpers.get_message(ApplicationStates.INFO_SELECTION))
                return True

            if event_origin == EventOrigin.SELECTIONCOMPLETE_MULTI:
                # extract element geometry and properties per type
                AllplanHelpers.log("[FormworkToRebarAttributes]","Extracting geometry and rebar elements",False)
                selection_geometry = AllplanHelpers.filter_drawing_elements_for_geometry(self.user_mulitselection_list)
                selection_reinforcement = AllplanHelpers.filter_drawing_elements_for_rebar(self.user_mulitselection_list)
                if(not selection_geometry and selection_reinforcement):
                    self.lock_user_interface(False)
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_NO_GEOMETRY_SELECTED), AllplanUtil.MB_OK)
                    return False
                if(selection_geometry and not selection_reinforcement):
                    self.lock_user_interface(False)
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_NO_REINFORCEMENT_SELECTED), AllplanUtil.MB_OK)
                    return False
                if(not selection_geometry and not selection_reinforcement):
                    self.lock_user_interface(False)
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_NOTHING_SELECTED), AllplanUtil.MB_OK)
                    return False
                rebar_container_list = []
                geometry_container_list = []

                # create the rebar element containers
                AllplanHelpers.log("[FormworkToRebarAttributes]","Calculating global reference points for rebar shapes",False)
                found_unsupported_rebar  = False
                for reinforcement_object in selection_reinforcement:
                    temp_rebar = RebarContainer(reinforcement_object)
                    if temp_rebar.get_global_reference():
                        rebar_container_list.append(temp_rebar)
                    else:
                        AllplanHelpers.log("[FormworkToRebarAttributes]","!!! shape exception for mark: " + temp_rebar.get_rebar_mark(),False)
                        found_unsupported_rebar = True

                if found_unsupported_rebar:
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_UNSUPPORTED_REBAR_SHAPE), AllplanUtil.MB_OK)

                AllplanHelpers.infinite_progressbar_start("Calculating Geometry Containment","This can take a while")
                # create the geometric element containers and add the reinforcement containers if they are inside
                AllplanHelpers.log("[FormworkToRebarAttributes]","Processing rebar and geometry containment algoritm",False)
                for geometry_object in selection_geometry:
                    temp_geo = GeometryContainer(geometry_object)
                    for index, rebar_container in enumerate(rebar_container_list):
                        if(not rebar_container.is_rebar_assigned_to_geometry()):
                            test = temp_geo.add_rebar_if_inside(rebar_container, float(self.attribute_settings["Tolerance"][0].value))
                            rebar_container_list[index].set_assigned_to_geometry(test)
                    geometry_container_list.append(temp_geo)

                # assign attributes to the reinforcement in the geometry_container_list>rebar_inside_list
                AllplanHelpers.log("[FormworkToRebarAttributes]","Transferring attributes to reinforcement",False)
                attribute_id_list = self.attribute_settings["AttributeIDFilter"][0].value
                if len(attribute_id_list) > 1:
                    attribute_id_list.pop() # remove trailing zero attribute

                reading_errors_list = []
                writing_errors_list = []

                for geometry_element in geometry_container_list:
                    geometry_element_attributes_list = AllplanHelpers.get_attributes_of_object(geometry_element.get_element_adapter())
                    if geometry_element_attributes_list:
                        allright_id = str(AllplanHelpers.linear_search(geometry_element_attributes_list,10)[1])
                        writable_attribute_list = []
                        for attribute_id in attribute_id_list:
                            attribute_tuple = AllplanHelpers.linear_search(geometry_element_attributes_list, attribute_id)
                            if attribute_tuple:
                                writable_attribute_list.append(attribute_tuple)
                        if len(writable_attribute_list) == 0:
                            AllplanHelpers.log("[FormworkToRebarAttributes]","!!! The requested attributes were not found on: " + allright_id,False)
                        success = AllplanHelpers.write_attributes_to_allplan(geometry_element.get_attached_rebar(), writable_attribute_list)
                        if not success:
                            for rb in geometry_element.get_attached_rebar():
                                AllplanHelpers.log("[FormworkToRebarAttributes]","!!! Failure to write attributes at mark: " + str(rb.get_rebar_mark()),False)
                            writing_errors_list.append(geometry_element)
                    else:
                        AllplanHelpers.log("[FormworkToRebarAttributes]","!!! Attributes not initialized on element! Allright_id not available.",False)
                        reading_errors_list.append(geometry_element)
                AllplanHelpers.log("[FormworkToRebarAttributes]","Transfer complete",False)
                AllplanHelpers.infinite_progressbar_stop()
                if len(reading_errors_list) > 0:
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_READING_ATTRIBUTES), AllplanUtil.MB_OK)
                if len(writing_errors_list) > 0:
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.ERROR_TRANSFERRING_ATTRIBUTES), AllplanUtil.MB_OK)
                if len(reading_errors_list) == 0 and len(writing_errors_list) == 0:
                    self.lock_user_interface(False)
                    AllplanUtil.ShowMessageBox(AllplanHelpers.get_message(ApplicationStates.INFO_FINISHED), AllplanUtil.MB_OK)
                    return True
                self.lock_user_interface(False)
                return False

        if self.get_event() == Event.OBJECT_CALCULATION:
            return True

    def lock_user_interface(self, is_locked):
        if is_locked:
            # lock user interface
            self.ctrl_prop_util.set_enable_function("Button", self.disable_variable_function)
            self.ctrl_prop_util.set_enable_function("Tolerance", self.disable_variable_function)
            self.attribute_settings["AttributeIDFilterVisibility"][0].value = 0
        else:
            self.ctrl_prop_util.set_enable_function("Button", self.enable_variable_function)
            self.ctrl_prop_util.set_enable_function("Tolerance", self.enable_variable_function)
            self.attribute_settings["AttributeIDFilterVisibility"][0].value = 1
            # workaround "list may not be empty upon visibility change" BUG
            temp_list = self.build_ele_list[0].AttributeIDFilter.value
            if 0 not in temp_list:
                temp_list.append(0)
            # update palette
            self.palette_service.update_palette(-1, True)

    def create_filter(self, filtered_elements):
        """ Create a filter of AllplanElementAdapter types

        Args:
            filtered_elements: List of AllplanElementadapter types
        """
        type_uuids = []
        for filtered_element in filtered_elements:
            type_uuids.append(AllplanIFW.QueryTypeID(filtered_element))
        return AllplanIFW.SelectionQuery(type_uuids)

    def on_cancel_function(self):
        # workaround "list may not be empty upon visibility change" BUG
        temp_list = self.build_ele_list[0].AttributeIDFilter.value
        if 0 not in temp_list:
            temp_list.append(0)
        self.palette_service.close_palette()
        AllplanHelpers.infinite_progressbar_stop()
        return True

    def on_preview_draw(self):
        return

    def on_mouse_leave(self):
        return

    def get_event(self):
        return self.user_origin_event

    def set_event(self, event):
        self.user_origin_event = event

    def set_selection_mode(self, type):
        self.user_selection_mode = type

    def get_selection_mode(self):
        return self.user_selection_mode

    def modify_element_property(self, page, name, value):
        # update palette if necessary
        update_palette = self.palette_service.modify_element_property(page, name, value)
        # workaround "list may not be empty upon visibility change" BUG
        temp_list = self.build_ele_list[0].AttributeIDFilter.value
        if 0 not in temp_list:
            temp_list.append(0)
        if update_palette:
            self.palette_service.update_palette(-1, False)

    def execute_load_favorite(self, file_name):
        """ load the favorite data """
        BuildingElementListService.read_from_file(file_name, self.build_ele_list)
        self.palette_service.update_palette(-1, True)

    def reset_param_values(self, _build_ele_list):
        BuildingElementListService.reset_param_values(self.build_ele_list)
        # workaround "list may not be empty upon visibility change" BUG
        temp_list = self.build_ele_list[0].AttributeIDFilter.value
        if 0 not in temp_list:
            temp_list.append(0)
        # update palette
        self.palette_service.update_palette(-1, True)

    def update_after_favorite_read(self):
        self.palette_service.update_palette(-1, True)

    def __del__(self):
        BuildingElementListService.write_to_default_favorite_file(self.build_ele_list)

    def set_active_palette_page_index(self, active_page_index: int):
        self.palette_service.update_palette(-1, False)


class AllplanHelpers():
    """Contains all helper methods to run the program.
    - most helper methods are self explanatory. methods preceded with __ are internal and should not be used outside of the Allplanhelper construct
    - keeps track of most of the data in the program
    """
    coord_input = None
    doc = None
    string_table = None
    first_run = True # identifier for progress bar if it needs to be created or a step needs to be set.
    progress_bar_infinite = None

    @staticmethod
    def log(location: str, message, is_error_message: bool):
        if(is_error_message):
            message = AllplanHelpers.get_exception_message(message)
        print(location + " -> " + message)

    @staticmethod
    def infinite_progressbar_start(title, description):
        AllplanHelpers.progress_bar_infinite = AllplanUtil.ProgressBar(0,0,False)
        AllplanHelpers.progress_bar_infinite.SetAditionalInfo(title)
        AllplanHelpers.progress_bar_infinite.SetInfinitProgressbar(True)

    @staticmethod
    def infinite_progressbar_stop():
        try:
            AllplanHelpers.progress_bar_infinite.CloseProgressbar()
        except:
            pass

    @staticmethod
    def static_init(coord_input, string_table: BuildingElementStringTable):
        AllplanHelpers.coord_input = coord_input
        AllplanHelpers.string_table = string_table
        AllplanHelpers.doc = coord_input.GetInputViewDocument()

    @staticmethod
    def show_message_in_taskbar(message: str):
        AllplanHelpers.coord_input.InitFirstElementInput(AllplanIFW.InputStringConvert(message))
        return

    @staticmethod
    def select_drawing_elements():
        selection_elementadapterlist = AllplanBaseElements.ElementsSelectService.SelectAllElements(AllplanHelpers.doc)
        if(selection_elementadapterlist ==  None):
            return False, None
        return True, selection_elementadapterlist

    @staticmethod
    def filter_drawing_elements_for_geometry(selection_elementadapterlist: AllplanElementAdapter):
        geometry_selection = []
        geometry_uuids = [AllplanElementAdapter.Slab_TypeUUID, AllplanElementAdapter.Column_TypeUUID,
                                             AllplanElementAdapter.Beam_TypeUUID, AllplanElementAdapter.WallTier_TypeUUID,
                                             AllplanElementAdapter.Volume3D_TypeUUID, AllplanElementAdapter.BRep3D_Volume_TypeUUID,
                                             AllplanElementAdapter.Cylinder3D_TypeUUID, AllplanElementAdapter.Sphere3D_TypeUUID]
        # first get the rebar and save it to a smaller list to work with
        for element in selection_elementadapterlist:
            if(element.GetElementAdapterType().GetGuid() in geometry_uuids):
                geometry_selection.append(element)
        if(len(geometry_selection) == 0):
            return None
        else:
            return geometry_selection

    @staticmethod
    def filter_drawing_elements_for_rebar(selection_elementadapterlist: AllplanElementAdapter):
        rebar_selection = []
        placement_uuids = [AllplanElementAdapter.BarsLinearPlacement_TypeUUID,
                           AllplanElementAdapter.BarsLinearMultiPlacement_TypeUUID,
                           AllplanElementAdapter.BarsAreaPlacement_TypeUUID,
                           AllplanElementAdapter.BarsSpiralPlacement_TypeUUID,
                           AllplanElementAdapter.BarsCircularPlacement_TypeUUID,
                           AllplanElementAdapter.BarsRotationalSolidPlacement_TypeUUID,
                           AllplanElementAdapter.BarsRotationalPlacement_TypeUUID,
                           AllplanElementAdapter.BarsTangentionalPlacement_TypeUUID,
                           AllplanElementAdapter.BarsEndBendingPlacement_TypeUUID]
        # first get the rebar and save it to a smaller list to work with
        for element in selection_elementadapterlist:
            attributes = element.GetAttributes(AllplanBaseElements.eAttibuteReadState.ReadAllAndComputable)
            ifc_class = AllplanHelpers.linear_search(attributes, 684)
            if(not ifc_class == None):
                ifc_class = ifc_class[1]
                if(ifc_class == "IfcReinforcingBar" and element.GetElementAdapterType().GetGuid() in placement_uuids):
                    rebar_selection.append(element)
        if(len(rebar_selection) == 0):
            return None
        else:
            return rebar_selection

    @staticmethod
    def is_point_located_inside_geometry(geometry_element, point) -> bool:
        test = AllplanGeometry.Comparison.DeterminePosition(geometry_element,point, 0)
        return test

    @staticmethod
    def get_exception_message(exc: Exception) -> str:
        if hasattr(exc, 'message'):
            return exc.Message
        else:
            return exc.args[0]

    @staticmethod
    def get_message(message: ApplicationStates, data = None):
        msg_number = 9000 + message.value
        msg = AllplanHelpers.string_table.get_string(str(msg_number), "String not found: " + message.name)
        if(data):
            if(type(data) is str):
                msg = msg + " " + data
            else:
                msg = msg + " " + '-'.join(str(x.value) for x in data)
        return msg

    @staticmethod
    def linear_search(data, target):
        for tup in data:
            if target in tup:
                return tup
        return None

    @staticmethod
    def get_user_attribute_settings(palette: BuildingElement):
        # get the attribute definitions from the palette
        attribute_preferences = {}
        attribute_preferences["AttributeIDFilter"] = [palette.AttributeIDFilter]
        attribute_preferences["Tolerance"] = [palette.Tolerance]
        attribute_preferences["SelectionButton"] = [palette.Button]
        attribute_preferences["AttributeIDFilterVisibility"] = [palette.is_attribute_filter_visible]
        # check if all attributes are defined
        for attr in attribute_preferences:
            if(str(attribute_preferences[attr][0].value) == "[0]"):
                return False, None
        return True, attribute_preferences

    @staticmethod
    def get_attributes_of_object(element_adapter):
        try:
            attributes = AllplanBaseElements.ElementsAttributeService.GetAttributes(element_adapter)
            return attributes
        except:
           return None


    @staticmethod
    def write_attributes_to_allplan(rebar_elements, attribute_list):
        if len(attribute_list) == 0:
            return False
        try:
            attributes = BuildingElementAttributeList()
            for attribute in attribute_list:
                try:
                    attributes.add_attribute(int(attribute[0]), attribute[1])
                except:
                    try:
                        attributes.add_attribute(int(attribute[0]), float(attribute[1]))
                    except:
                        attributes.add_attribute(int(attribute[0]), int(attribute[1]))
            attr_list = attributes.get_attributes_list_as_tuples()
            element_list = AllplanElementAdapter.BaseElementAdapterList()
            for rebar_element in rebar_elements:
                element_list.append(rebar_element.get_element_adapter())
            AllplanBaseElements.ElementsAttributeService.ChangeAttributes(attr_list, element_list)
            return True
        except:
            return False


class RebarContainer():

    def __init__(self, element_adapter):
        self.element_adapter = element_adapter
        self.global_reference = self.__calculate_global_reference()
        self.is_assigned_to_geometry = False

    def get_element_adapter(self):
        return self.element_adapter

    def __calculate_global_reference(self):
        try:
            bar_placement = AllplanBaseElements.GetElement(self.element_adapter)
            bending_shape = bar_placement.BendingShape
            local_to_global = bar_placement.GetPlacementMatrix()
            bending_shape.Transform(local_to_global)
            global_reference = bending_shape.ShapePolyline
            return global_reference
        except:
            return None

    def get_global_reference(self):
        return self.global_reference

    def set_assigned_to_geometry(self, assigned_bool):
        self.is_assigned_to_geometry = assigned_bool

    def is_rebar_assigned_to_geometry(self):
        return self.is_assigned_to_geometry

    def get_placement_type(self):
        return self.element_adapter.GetElementAdapterType().GetGuid()

    def get_rebar_mark(self):
        parent_element = AllplanElementAdapter.BaseElementAdapterParentElementService.GetParentElement(self.element_adapter)
        rebarmark = AllplanElementAdapter.ReinforcementPropertiesReader.GetPositionNumber(parent_element)
        return str(rebarmark)

    def get_placement_uuid(self):
        return self.element_adapter.GetElementUUID()


class GeometryContainer():

    def __init__(self, element_adapter):
        self.element_adapter = element_adapter
        self.global_reference = self.__calculate_global_reference()
        self.rebar_inside_list = []

    def get_element_adapter(self):
        return self.element_adapter

    def __calculate_global_reference(self):
        reference_geometry = self.element_adapter.GetGeometry()
        return reference_geometry

    def get_global_reference(self):
        return self.global_reference

    def get_attached_rebar(self):
        return self.rebar_inside_list

    def add_rebar_if_inside(self, rebar_container: RebarContainer, tolerance_percentage) -> bool:
        polyline = rebar_container.get_global_reference()
        if polyline:
            point_count = len(polyline.Points)
            positive_count = 0
            for point in polyline.Points:
                test = AllplanHelpers.is_point_located_inside_geometry(self.global_reference,point)
                if(test == AllplanGeometry.eComparisionResult.eInside):
                    positive_count +=1
                else:
                    pass
            try:
                percentage_inside = positive_count / point_count
            except ZeroDivisionError:
                percentage_inside = 0
            if percentage_inside == 0:
                return False
            elif tolerance_percentage > percentage_inside:
                return False
            else:
                self.rebar_inside_list.append(rebar_container)
                return True
        return False


