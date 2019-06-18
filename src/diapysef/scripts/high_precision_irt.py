#!/usr/env python

# WRITE A COMMANDLINE TOOL FOR HIGH-PRECISION IRT LIBRARY GENERATION
# FOR THE OPENSWATH tr_irt_nonlinear option

import numpy as np
import re
import pandas as pd
import os
import sys

if len(sys.argv) < 4:
    print("Usage: high_precision_irt.py mqout_dir output_file peptide_number_cutoff")
    print("Description: This script will generate a set of "high precision iRT" peptides as described in Bruderet et al (2016) from MaxQuant output to derive a set of conserved, high-intensity peptides.") 
    sys.exit()

mqout_dir = sys.argv[1]
# mqout_dir can be 1 MQ output from multiple runs or a directory that holds
# multiple MQ out files 

outfile = sys.argv[2]
# One single output high_precision_iRT.txt

cutoff = int(sys.argv[3] )
# Peptide number cutoff

filenames = []
for root, dirs, files in os.walk(mqout_dir):
     for name in files:
         #print(os.path.join(root, name))
         filenames.append(os.path.join(root, name))

r = re.compile(".*msms.txt")

msms_files = list(filter(r.findall, filenames))

msms = []
sequence = []
for i in msms_files:
    stat = pd.read_csv(i, sep = '\t')
    msms.append(pd.read_csv(i, sep = '\t'))
    sequence.append(stat['Modified sequence'].to_list())

# get the intersection peptides

intersection_peptides = list(set.intersection(*map(set, sequence)))
print(len(intersection_peptides))


pep = []
for i in msms: pep.append(i['PEP'].mean())

msms_irt = msms[np.argmin(pep)]

msms_irt = msms_irt.loc[msms_irt['Modified sequence'].isin(intersection_peptides)]

msms_irt = msms_irt.sort_values("PEP", ascending = True)
msms_irt = msms_irt.drop_duplicates(subset = "Modified sequence")
msms_irt = msms_irt.rename(columns = {'Modified sequence' : "ModifiedPeptideSequence"})

ev_file = os.path.join(os.path.dirname(msms_files[np.argmin(pep)]), 'evidence.txt')
ev = pd.read_csv(ev_file, sep = '\t')
ev = ev.loc[:, ["id", "Calibrated retention time", 'Calibrated 1/K0', 'Ion mobility index']]
ev = ev.rename(columns = {'id':'Evidence ID', 'Calibrated 1/K0':'PrecursorIonMobility'})
ms = pd.merge(msms_irt, ev, on = 'Evidence ID')

rt = ms.loc[:, 'Calibrated retention time']
NormalizedRT = (rt - min(rt)) / (max(rt) - min(rt)) * 100

ms['NormalizedRetentionTime'] = NormalizedRT

ms = ms[ms['PEP'] < 0.01]
ms = ms[ms['Score'] > ms['Score'].quantile(0.5)]
ms = ms[ms['Peak coverage'] > ms['Peak coverage'].quantile(0.2)]
ms = ms.sort_values("PEP", ascending = True)

ms = ms[0: cutoff]


ms1 = ms.loc[:, ["id", "m/z", "Masses", "Charge", "NormalizedRetentionTime","PrecursorIonMobility", "Intensities", "Sequence", "ModifiedPeptideSequence","Proteins"]]

masses = ms1['Masses'].str.split(';', expand =True).stack().str.strip().reset_index(level = 1, drop=True)

intensities = ms1['Intensities'].str.split(';', expand =True).stack().str.strip().reset_index(level = 1, drop=True)

df1 = pd.concat([masses, intensities], axis = 1, keys = ['Masses','Intensities'])

ms12 = ms1.drop(['Masses', 'Intensities'], axis = 1)
ms12 = ms12.join(df1).reset_index(drop = True)
ms12.columns = ['transition_group_id', 'PrecursorMz', 'PrecursorCharge','NormalizedRetentionTime', 'PrecursorIonMobility', 'PeptideSequence','ModifiedPeptideSequence', 'ProteinName', 'ProductMz', 'LibraryIntensity']

ms12['decoy'] = 0
ms12['transition_name'] = ['_'.join(str(i) for i in z) for z in zip(ms12.transition_group_id,ms12.PrecursorMz,ms12.ProductMz)]

ms12=ms12.drop_duplicates()

ms12.to_csv(outfile, sep = "\t", index=False)





