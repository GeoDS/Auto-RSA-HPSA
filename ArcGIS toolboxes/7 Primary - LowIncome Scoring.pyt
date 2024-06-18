# -*- coding: utf-8 -*-

import arcpy
arcpy.env.overwriteOutput = True

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "LowIncome Scoring"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "LowIncome Scoring"
        self.description = "Calculate the low income score for each RSA"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        #first parameter
        param0 = arcpy.Parameter(
        displayName="RSA",
        name="rsa",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Input")
        
        param1 = arcpy.Parameter(
        displayName="output_name",
        name="rsa_scores",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Output")
        
        params = [param0, param1]

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
        rsa = parameters[0].valueAsText
        outfeature = parameters[1].valueAsText

        #find the correct name for all fields
        field_names = [f.name for f in arcpy.ListFields(rsa)]
        field_names_str = ' '.join(field_names)
        arcpy.AddMessage("Field names: {}.".format(field_names_str))
        def add_underscore(field):
            return field.replace(' ', '_')

        ca_flag = False
        for name in field_names:
            arcpy.AddMessage(name)
            if 'poverty' in name:
                poverty = name
                poverty = add_underscore(poverty)
                continue
            if 'pop' in name and 'lwinc' in name and 'water' not in name:
                pop_lwinc = name
                pop_lwinc = add_underscore(pop_lwinc)
            if 'pop' in name and 'lwinc' not in name and 'water' not in name:
                pop = name
                pop = add_underscore(pop)
            if 'clusterid' in name or 'hsanum' in name:
                clusterid = name
                clusterid = add_underscore(clusterid)
            if 'birth' in name or 'brth' in name:
                birth = name
                birth = add_underscore(birth)
            if 'lbw' in name:
                lbw = name
                lbw = add_underscore(lbw)
            if 'dth' in name:
                dth = name
                dth = add_underscore(dth)
            if 'primary_time' in name:
                time = name
                time = add_underscore(time)
            if 'primary_distance' in name:
                distance = name
                distance = add_underscore(distance)
            if 'pc_lwinc' in name or 'fte_lw' in name:
                fte = name
                fte = add_underscore(fte)
                arcpy.AddMessage(fte)
            if 'CA_constraint' in name:
                ca_constraint = name
                ca_flag = True
    
        #field_list = [poverty,pop,clusterid, birth, lbw, dth, \
        #              time, distance]

            
        #arcpy.CopyFeatures_management(joined_feature, outfeature)
        arcpy.management.CopyFeatures(rsa, outfeature)
        
        #calculate the first scoring criterion
        fieldname1 = "pop_fte_ratio"
        fieldname2 = "pop_score"
        arcpy.AddField_management(outfeature, fieldname1 , "DOUBLE", 18,11)
        arcpy.AddField_management(outfeature, fieldname2 , "SHORT", 18,11)
        field_names = [f.name for f in arcpy.ListFields(outfeature)]
        arcpy.AddMessage(field_names)
        if '_' not in field_names:
            pop = pop.replace('.', '_')
            fte = fte.replace('.', '_')
        arcpy.AddMessage([fte in field_names])    
        expression1 = "ratio(!" + pop_lwinc + "!,!" + fte + "!)"
        arcpy.AddMessage(expression1)
        codeblock1 = """def ratio(pop_int, FTE_sum):
            if FTE_sum == 0 or FTE_sum == None:
                return math.inf
            else:
                value = pop_int/FTE_sum
                return value """
            
        arcpy.CalculateField_management(outfeature, fieldname1, expression1, "PYTHON3", codeblock1)
        
        
        expression2 = "rate(!"+ pop + "!,!pop_fte_ratio!)"
        codeblock2 = """def rate(pop_int, ratio):
            if ratio == math.inf:
                if pop_int>= 2500:
                    return 5
                elif pop_int >= 2000:
                    return 4
                elif pop_int >= 1500:
                    return 3
                elif pop_int >= 1000:
                    return 2
                elif pop_int >= 500:
                    return 1
                else:
                    return 0
            else:
                value = ratio
                if value > 10000:
                    return 5
                elif value >= 5000:
                    return 4
                elif value >= 4000:
                    return 3
                elif value >= 3500:
                    return 2
                elif value >= 3000:
                    return 1
                elif value < 3000:
                    return 0 """

        arcpy.CalculateField_management(outfeature, fieldname2, expression2, "PYTHON3", codeblock2)


        ###second criterion
        fieldname1 = "poverty_ratio"
        fieldname2 = "poverty_score"

        arcpy.AddField_management(outfeature, fieldname1 , "DOUBLE", 18,11)
        arcpy.AddField_management(outfeature, fieldname2 , "SHORT", 18,11)

        if '_' not in field_names:
            poverty = poverty.replace('.', '_')
            
        expression1 = "ratio(!" + pop + "!,!" + poverty + "!)"
        codeblock1 = """def ratio(pop_int, poverty):
            if pop_int == 0 or pop_int == None:
                return 0
            else:
                value = poverty/pop_int
                return value """

        arcpy.CalculateField_management(outfeature, fieldname1, expression1, "PYTHON3", codeblock1)


        expression2 = "rate(!poverty_ratio!)"
        codeblock2 = """def rate(poverty_float):
            poverty_float = poverty_float*100
            if poverty_float >= 50:
                return 5
            elif poverty_float >= 40:
                return 4
            elif poverty_float >= 30:
                return 3
            elif poverty_float >= 20:
                return 2
            elif poverty_float >= 15:
                return 1
            else:
                return 0
        """
        
        arcpy.CalculateField_management(outfeature, fieldname2, expression2, "PYTHON3", codeblock2)

        ################################
        #infant health score

        arcpy.AddField_management(outfeature, 'lbw' , "DOUBLE", 18,11)
        arcpy.AddField_management(outfeature, 'imr' , "DOUBLE", 18,11)
        arcpy.AddField_management(outfeature, "infant_score" , "SHORT", 18,11)


        if '_' not in field_names:
            lbw = lbw.replace('.', '_')
            dth = dth.replace('.', '_')
            birth = birth.replace('.', '_')
        
        exp_lbw = "!" + lbw + "! *100/!" + birth +"!"
        arcpy.CalculateField_management(outfeature, 'lbw', exp_lbw, "PYTHON3")

        exp_imr = "!" + dth + "! *1000/!" + birth +"!"
        arcpy.CalculateField_management(outfeature, 'imr', exp_imr, "PYTHON3")        

        expression3 = "rate(!lbw!, !imr!)"
        codeblock3 = """def rate(lbw, imr):
            if imr >= 20 or lbw >= 13:
                return 5
            elif 18 <= imr < 20 or 11 <= lbw < 13:
                return 4
            elif 15 <= imr < 18 or 10 <= lbw < 11:
                return 3
            elif 12 <= imr < 15 or 9 <= lbw < 10:
                return 2
            elif 10 <= imr < 12 or 7 <= lbw < 9:
                return 1
            elif imr < 10 or lbw < 7:
                return 0
        """
        arcpy.CalculateField_management(outfeature, "infant_score", expression3, "PYTHON3", codeblock3)        


        
        #############################################
        #calculate NSC score
        nsc_score = "nsc_score"
        arcpy.AddField_management(outfeature, nsc_score , "SHORT", 18,11)
        if '_' not in field_names:
            time = time.replace('.', '_')
            distance = distance.replace('.', '_')
            
        expression4 = "rate(!" + time + "!, !" + distance + "!)"
        codeblock4 = """def rate(time, dis):
            if time >= 60 or dis >= 50:
                return 5
            elif 50 <= time < 60 or 40 <= dis < 50:
                return 4
            elif 40 <= time < 50 or 30 <= dis < 40:
                return 3
            elif 30 <= time < 40 or 20 <= dis < 30:
                return 2
            elif 20 <= time < 30 or 10 <= dis < 20:
                return 1
            elif time < 20 or dis < 10:
                return 0
        """
        
        arcpy.CalculateField_management(outfeature, nsc_score, expression4, "PYTHON3", codeblock4)        


        #calculate the final scores
        arcpy.AddField_management(outfeature, "score" , "SHORT", 18,11)
        expression5 = "!pop_score!*2 + !poverty_score! + !infant_score!+ !nsc_score!"
        arcpy.CalculateField_management(outfeature, "score", expression5, "PYTHON3")

        #add the population:fte constraint
        arcpy.AddField_management(outfeature, "pop_fte_contraint" , "SHORT", 18,11)
        expression7 = "rate(!"+ pop_lwinc + "!,!pop_fte_ratio!)"
        codeblock5 = """def rate(pop, ratio):
            if ratio == math.inf:
                if pop >= 500:
                    return 1
                else:
                    return 0
            elif ratio >= 3000:
                return 1
            else:
                return 0
        """
        arcpy.CalculateField_management(outfeature, "pop_fte_contraint", expression7, "PYTHON3", codeblock5)

        #add the population percent constraint
        arcpy.AddField_management(outfeature, "lwinc_perc" , "Double", 18,11)
        expression8 = "!"+ pop_lwinc + "!/!" + pop + "!"
        arcpy.CalculateField_management(outfeature, "lwinc_perc", expression8, "PYTHON3")

        arcpy.AddField_management(outfeature, "lwinc_constraint" , "SHORT", 18,11)
        expression9 = "rate(!lwinc_perc!)"
        codeblock6 = """def rate(lwinc_perc):
            if lwinc_perc == math.inf:
                return 0
            elif lwinc_perc >= 0.3:
                return 1
            else:
                return 0
        """
        arcpy.CalculateField_management(outfeature, "lwinc_constraint", expression9, "PYTHON3", codeblock6)

        arcpy.AddField_management(outfeature, "HPSA_scores" , "SHORT", 18,11)
        expression9 = "!score!*!pop_fte_contraint!*!lwinc_constraint!"
        arcpy.CalculateField_management(outfeature, "HPSA_scores", expression9, "PYTHON3")

        if ca_flag:
            arcpy.AddField_management(outfeature, "HPSA_scores_CA" , "SHORT", 18,11)
            expression8 = "!score!*!pop_fte_contraint!*!lwinc_constraint!*!" + ca_constraint + "!"
            arcpy.CalculateField_management(outfeature, "HPSA_scores_CA", expression8, "PYTHON3")


        return




    
