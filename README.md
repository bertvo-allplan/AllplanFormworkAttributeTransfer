# Transfer Attributes from 3D Formwork to Rebar placements in Allplan

This plugin includes one PythonPart scripts that assists you in performing the following tasks with ALLPLAN:

* Transferring a user-made selection of attributes from 3D formwork objects (3D volumes, architectural objects...) to rebar elements. (multiselection is possible)
* Defining the tolerance value that is needed to allow attribute transfer.

> [!TIP]
> A higher tolerance value results in the reinforcement to be less likely attached to a 3D geometry object.
> Overlap checking is based upon polygon points: [Amount of points in rebar shape]/[total points] = [tolerance].
> Circular reinforcement is considered to be a line of two points indicating the radius and centerpoint.


![image](https://github.com/user-attachments/assets/e0202411-f07a-4c96-bd9d-d0a11ff93d08)



# Installation
You can install this plugin from the plugin manager directly in ALLPLAN. 

Alternatively, you can also download the ALLEP package from the [release page](https://github.com/bertvo-allplan/AllplanFormworkAttributeTransfer/releases). And drag and drop the package into ALLPLAN to install it.

You need at least _ALLPLAN 2026_ to install the package.

## Installed PythonPart Script
After installation, you can find the following PythonPart script: `assignobjectattributestorebar.PYP`
in the ALLPLAN Library:
`Office` → `ALLPLAN GmbH` → `Assign Formwork Attributes to Rebar`

Alternatively, you can add the tool to the toolbar through "Actionbar Configuration" (restart of Allplan might be required)

![image](https://github.com/user-attachments/assets/16ad319a-55a6-47ad-8340-5cc9da4fde98)

# Any Issues?
If you have identified any issues, please [open an issue](https://github.com/bertvo-allplan/AllplanFormworkAttributeTransfer/issues).
