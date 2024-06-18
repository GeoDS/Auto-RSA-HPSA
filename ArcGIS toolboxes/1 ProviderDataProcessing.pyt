# -*- coding: utf-8 -*-

import arcpy
arcpy.env.overwriteOutput = True

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Provider Data Processing"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Provider Data"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
        displayName="provider table",
        name="providers",
        datatype="DETable",
        parameterType="Required",
        direction="Input")
        
        """
        param1 = arcpy.Parameter(
        displayName="output_provider",
        name="output_provider",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Output")
        """
        
        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        provider = parameters[0].valueAsText #shapefile
        provider_output = "ProvidersAll"

        ##make xy layer
        arcpy.management.MakeXYEventLayer(provider, 'Longitude', 'Latitude', 'provider_lyr')
        sr = arcpy.SpatialReference("USA Contiguous Albers Equal Area Conic")
        arcpy.management.Project('provider_lyr', provider_output, sr)
        #arcpy.CopyFeatures_management('provider_lyr', provider_output)
        

        ##generate three types of provider

        ##Primary Care
        primary_exp = "Discipline = 'PC' And Status = 'Eligible'"
        provider_output, r2 = arcpy.SelectLayerByAttribute_management(provider_output, 'NEW_SELECTION', 
                                        primary_exp)
        arcpy.AddMessage("There are {} providers selected for Primary Care.".format(r2))        
        primary_output = "Primary_providers"
        arcpy.CopyFeatures_management(provider_output, primary_output)


        #calculate the FTE
        arcpy.AddField_management(primary_output, "FTE" , "Double")

        expression = "min(1,rate(!Direct_Tour_Hours!, !Intern_or_Resident_!, !J1_Visa_Waiver_Holder_!))"
        codeblock = """def rate(hours, resident, j1):
        if resident == 'Yes':
            return 0.1
        if j1 == 'Yes':
            return 0
        return hours/40.0
        """
 
        arcpy.CalculateField_management(primary_output, "FTE", expression, "PYTHON3", codeblock)

        #calculate the low income FTE
        arcpy.AddField_management(primary_output, "FTE_lwinc" , "Double")

        expression1 = "min(1,rate(!Direct_Tour_Hours!, !Annual_Medicaid_Claims!, !Sliding_Fee__!, !Medicaid_Patient__!, !Intern_or_Resident_!, !J1_Visa_Waiver_Holder_!))"
        codeblock1 = """def rate(hours, mel_claim, sliding_fee, med_perc, resident, j1):
        if resident == 'Yes':
            return 0.1
        if j1 == 'Yes':
            return 0
        if mel_claim is not None:
            return mel_claim/5000.0 + hours/40.0*sliding_fee/100
        else:
            return hours/40.0*(sliding_fee + mde_perc)/100
        
        """ 
        
        arcpy.CalculateField_management(primary_output, "FTE_lwinc", expression1, "PYTHON3", codeblock1)

        ###output the lowincome provider
        lwinc_exp = "FTE_lwinc > 0"
        provider_lw_output, r2 = arcpy.SelectLayerByAttribute_management(primary_output, 'NEW_SELECTION', 
                                        lwinc_exp)
        arcpy.AddMessage("There are {} providers selected for Primary Care with Low Income Population.".format(r2))        
        primary_lw_output = "Primary_lwinc_providers"
        arcpy.CopyFeatures_management(provider_lw_output, primary_lw_output)       
        
        ##Dental Care
        dental_exp = "Discipline = 'DH' And Status = 'Eligible'"
        dental, count = arcpy.SelectLayerByAttribute_management(provider_output, 'NEW_SELECTION', 
                                        dental_exp)
        arcpy.AddMessage("There are {} providers selected for Dental Care.".format(count))        
        dental_output = "Dental_providers"
        arcpy.CopyFeatures_management(dental, dental_output)


        #calculate the low income Dental FTE
        arcpy.AddField_management(dental_output, "FTE_lwinc" , "Double")

        expression2 = "min(1,rate(!Direct_Tour_Hours!, !Annual_Medicaid_Claims!, !Sliding_Fee__!, !Medicaid_Patient__!, !J1_Visa_Waiver_Holder_!))"
        codeblock2 = """def rate(hours, mel_claim, sliding_fee, med_perc, j1):
        if j1 == 'Yes':
            return 0
        if mel_claim is not None:
            return mel_claim/4000.0 + hours/40.0*sliding_fee/100
        else:
            return hours/40.0*(sliding_fee + mde_perc)/100
        
        """
        arcpy.CalculateField_management(dental_output, "FTE_lwinc", expression2, "PYTHON3", codeblock2)

        ###output the lowincome dental provider
        lwinc_exp = "FTE_lwinc > 0"
        dental_lw, r2 = arcpy.SelectLayerByAttribute_management(dental_output, 'NEW_SELECTION', 
                                        lwinc_exp)
        arcpy.AddMessage("There are {} providers selected for Dental Care with Low Income Population.".format(r2))        
        dental_lw_output = "Dental_lwinc_providers"
        arcpy.CopyFeatures_management(dental_lw, dental_lw_output)       
        

        ##Mental Care
        exp = "Discipline = 'MH' And Status = 'Eligible' And Specialty = 'Psychiatrist'"
        mental, count = arcpy.SelectLayerByAttribute_management(provider_output, 'NEW_SELECTION', 
                                        exp)
        arcpy.AddMessage("There are {} providers selected for Mental Care.".format(count))        
        mental_output = "Mental_providers"
        arcpy.CopyFeatures_management(mental, mental_output)
        
        '''#calculate the FTE for Core Mental Health
        arcpy.AddField_management(mental_output, "Core_FTE" , "Double")

        expression = "min(1,rate(!Direct_Tour_Hours!, !Intern_or_Resident_!, !J1_Visa_Waiver_Holder_!))"
        codeblock = """def rate(hours, resident, j1):
        if j1 == 'Yes':
            return 0
        if resident == 'Yes':
            return 0.5
        return hours/40.0
        """
        '''
 
        #arcpy.CalculateField_management(mental_output, "core_FTE", expression, "PYTHON3", codeblock)


        #calculate the FTE for psychiatrists
        arcpy.AddField_management(mental_output, "psy_FTE" , "Double")

        expression3 = "min(1,rate(!Direct_Tour_Hours!, !Intern_or_Resident_!, !J1_Visa_Waiver_Holder_!, !Specialty!))"
        codeblock3 = """def rate(hours, resident, j1, spec):
        if spec != 'Psychiatrist':
            return 0
        if j1 == 'Yes':
            return 0
        if resident == 'Yes':
            return 0.5
        return hours/40.0
        """
 
        arcpy.CalculateField_management(mental_output, "psy_FTE", expression3, "PYTHON3", codeblock3)
        
        return
