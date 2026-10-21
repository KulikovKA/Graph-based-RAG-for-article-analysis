"""Explicit source-only curation for remaining DEV; ontology gaps are retained."""
import argparse
from campaign_helpers import Record, q


def D004():
    d=Record('D004')
    d.s('S1','''sens|extremely high and selective sensitivity|PERFORMANCE|high selective NO2 sensitivity
no2|NO 2|ANALYTE|nitrogen dioxide
mat|graphene–SnO 2 nanocomposites|MATERIAL|graphene–SnO2 nanocomposite
fabricate|fabricating graphene–SnO 2 nanocomposites|PROCESS|nanocomposite fabrication
oven|commercial microwave oven|DEVICE|microwave oven''')
    d.r('mat','HAS_PERFORMANCE','sens');d.r('mat','USED_FOR','no2')
    d.r('mat','FABRICATED_BY','fabricate',q=[q('S1','commercial microwave oven','equipment')])
    d.s('S2','''character|Structural characterization|PROCESS|structural characterization
products|products|MATERIAL|graphene–SnO2 nanocomposite
agglomerate|agglomerated structures|MORPHOLOGY|agglomerated structure
graphene|graphene|MATERIAL|graphene
sno2|SnO 2 particles|MATERIAL|SnO2 particles
snox|SnO x ( x ≤ 2) nanoparticles|MATERIAL|SnOx nanoparticles x≤2
small|small secondary|MORPHOLOGY|small secondary particle morphology
surface|surfaces|MORPHOLOGY|nanocomposite surface''')
    d.rs('''character ACTS_ON products
products HAS_MORPHOLOGY agglomerate
products HAS_COMPONENT graphene
products HAS_COMPONENT sno2
snox HAS_MORPHOLOGY small''')
    d.r('products','HAS_COMPONENT','snox',q=[q('S2','deposited on the surfaces','location')])
    d.s('S3','''oxygen|oxygen atomic ratio|PROPERTY|oxygen atomic ratio
phase|SnO x ( x < 2) phase|MATERIAL|SnOx phase x<2
appearance|appearance of an SnO x ( x < 2) phase|PROCESS|SnOx phase appearance''')
    d.r('products','HAS_PROPERTY','oxygen',q=[q('S3','decreased','trend'),q('S3','with the appearance of an SnO x ( x < 2) phase','associated_change')])
    d.s('S4','''treat|microwave treatment|PROCESS|microwave treatment
mat4|graphene–SnO 2 nanocomposites|MATERIAL|graphene–SnO2 nanocomposite
graphene4|graphene|MATERIAL|graphene|energy_transport_promoter|2
transport|efficient transport of the microwave energy|PROCESS|microwave energy transport
evap|evaporation and redeposition of SnO x nanoparticles|PROCESS|SnOx evaporation/redeposition
snox4|SnO x nanoparticles|MATERIAL|SnOx nanoparticles unspecified x''')
    d.rs('''treat ACTS_ON mat4
graphene4 FACILITATES transport
treat FACILITATES evap
evap ACTS_ON snox4''')
    d.s('S5','''mat5|graphene–SnO 2 nanocomposites|MATERIAL|graphene–SnO2 nanocomposite
response|high sensor response|PERFORMANCE|sensor response
no25|NO 2|ANALYTE|nitrogen dioxide
temp|150 °C|OPERATING_CONDITION|150 °C''')
    d.r('mat5','HAS_PERFORMANCE','response',q=[q('S5','24.7','response',24.7),q('S5','1 ppm of NO 2','analyte_concentration',1,'ppm'),q('S5','150 °C','temperature',150,'°C'),q('S5','optimized temperature','temperature_selection')])
    d.r('mat5','USED_FOR','no25')
    d.s('S6','''mat6|graphene–SnO 2 nanocomposites|MATERIAL|graphene–SnO2 nanocomposite
selectivity|selectively sensitive|PERFORMANCE|NO2 selectivity
no26|NO 2|ANALYTE|nitrogen dioxide
so2|SO 2|ANALYTE|sulfur dioxide|comparison_analyte
nh3|NH 3|ANALYTE|ammonia|comparison_analyte
ethanol|ethanol|ANALYTE|ethanol|comparison_analyte''')
    d.r('mat6','HAS_PERFORMANCE','selectivity',mode='COMPARED',q=[q('S6','NO 2 gas, in comparison with SO 2, NH 3, and ethanol gases','comparison')])
    d.s('S7','''generate|generation of SnO x nanoparticles and the SnO x phase in the matrix|PROCESS|SnOx generation
nanoparticles7|SnO x nanoparticles|MATERIAL|SnOx nanoparticles unspecified x
phase7|SnO x phase|MATERIAL|SnOx phase unspecified x
formation|formation of SnO 2 /SnO 2 homojunctions, SnO 2 /SnO x ( x < 2) heterojunctions, and SnO 2 /graphene heterojunctions|PROCESS|junction formation
homo|SnO 2 /SnO 2 homojunctions|MORPHOLOGY|SnO2 homojunction|electronic_interface
hetero1|SnO 2 /SnO x ( x < 2) heterojunctions|MORPHOLOGY|SnO2/SnOx heterojunction|electronic_interface
hetero2|SnO 2 /graphene heterojunctions|MORPHOLOGY|SnO2/graphene heterojunction|electronic_interface
sens7|excellent sensitivity|PERFORMANCE|high selective NO2 sensitivity
mat7|graphene–SnO 2 nanocomposites|MATERIAL|graphene–SnO2 nanocomposite
no27|NO 2|ANALYTE|nitrogen dioxide''')
    d.r('generate','CAUSES','formation',mode='PROPOSED',note='Авторы предполагают образование junctions при генерации SnOx; FACILITATES не сохраняет утверждение results in.')
    for j in ['homo','hetero1','hetero2']:
        d.r(j,'EXPLAINS','sens7',mode='PROPOSED',note='Электронный интерфейс объясняет чувствительность; допустимого MORPHOLOGY → PERFORMANCE predicate нет.')
    d.r('mat7','HAS_PERFORMANCE','sens7',mode='PROPOSED',note='Proposed explanation context; no independent confirmation of junction mechanism.')
    d.s('S8','''defects|surface Sn interstitial defects|MORPHOLOGY|surface Sn interstitial defects|interfacial_defect
defectgen|generation of surface Sn interstitial defects|PROCESS|surface Sn interstitial defect generation
performance|excellent NO 2 sensing performance|PERFORMANCE|NO2 sensing performance
no28|NO 2|ANALYTE|nitrogen dioxide''')
    d.r('defectgen','EXPLAINS','performance',mode='PROPOSED',note='Частичный вклад дефектов в sensing performance; не равен общему процессу изготовления или измеренному IMPROVES.')
    d.identity('snox','phase','RELATED','Distinct particle/phase descriptions and different x bounds; not forced SAME.')
    for other in ['so2','nh3','ethanol']:d.identity('no26',other,'DIFFERENT','Explicit comparison chemicals; no negative detection inferred.')
    d.finish(['Q3 applied: only two direct FACILITATES edges; no transitive graphene-to-evaporation inference.',
              '24.7/1 ppm/150 °C attach only to S5 response. SnOx bounds and particle/phase forms remain distinct.',
              'S7 suggestions and S8 explanatory continuation retained as PROPOSED; unexpressible causal claims retained as candidates.'])


def D060():
    d=Record('D060')
    d.s('S1','''doping|molecular doping|PROCESS|molecular doping
sensitivity|sensitivity|PERFORMANCE|NH3 sensitivity
sensor|graphene sensors|DEVICE|graphene sensor
cvd|chemical vapor deposition|PROCESS|chemical vapor deposition
nh3|NH3|ANALYTE|ammonia
rt|room temperature|OPERATING_CONDITION|room temperature''')
    d.rs('''sensor FABRICATED_BY cvd
doping IMPROVES sensitivity''')
    d.r('sensor','DETECTS','nh3',q=[q('S1','room temperature','temperature')])
    d.s('S2','''doping2|doping an as-fabricated graphene sensor with NO2 gas|PROCESS|NO2 molecular doping
sensor2|as-fabricated graphene sensor|DEVICE|graphene sensor
no2|NO2|MATERIAL|nitrogen dioxide dopant|dopant
sensitivity2|sensitivity of its electrical resistance|PERFORMANCE|NH3 resistance sensitivity
adsorb|adsorption of NH3 molecules|PROCESS|NH3 adsorption
nh32|NH3|ANALYTE|ammonia''')
    d.r('doping2','ACTS_ON','sensor2',q=[q('S2','NO2 gas','dopant')])
    d.r('doping2','IMPROVES','sensitivity2',q=[q('S2','about an order of magnitude','improvement_factor')],note='NO2 is a dopant here; NH3 is the analyte.')
    d.s('S3','''doped|NO2-doped graphene sensor|DEVICE|NO2-doped graphene sensor
lod|detection limit|PERFORMANCE|detection limit
before|before doping|OPERATING_CONDITION|before NO2 doping''')
    d.r('doped','HAS_PERFORMANCE','lod',mode='COMPARED',q=[q('S3','∼200 parts per billion (ppb)','doped_detection_limit',200,'ppb'),q('S3','∼1400 ppb before doping','undoped_detection_limit',1400,'ppb')])
    d.s('S4','''electrical|Electrical characterization|PROCESS|electrical characterization
raman|Raman spectroscopy measurements|PROCESS|Raman spectroscopy
fet|graphene field-effect transistors|DEVICE|graphene field-effect transistor
adsorb4|adsorption of NO2 molecules|PROCESS|NO2 adsorption
no24|NO2|MATERIAL|nitrogen dioxide dopant|dopant
holes|hole concentration|PROPERTY|hole concentration
graphene|graphene|MATERIAL|graphene|charge_carrier_host|2
enhance|sensitivity enhancement|PERFORMANCE|NH3 sensitivity enhancement''')
    d.rs('''electrical ACTS_ON fet
raman ACTS_ON fet
fet USES_MATERIAL graphene
graphene HAS_PROPERTY holes''')
    d.r('adsorb4','INCREASES','holes',note='Увеличение концентрации носителей — направление изменения; не тождественно улучшению качества.')
    d.r('adsorb4','EXPLAINS','enhance',note='Адсорбция NO2 через повышение hole concentration объясняет усиление чувствительности; причинный effect не выражается ACTS_ON.')
    d.identity('sensor','doped','BROADER','Doped configuration is narrower than generic graphene sensor; do not merge before/after instances.')
    d.finish(['NO2 dopant and NH3 analyte roles preserved; no NO2 DETECTS inferred.',
              'LOD before/after and approximate factor preserved; experiment is asserted, not hypothetical.'])


def D078():
    d=Record('D078')
    d.s('S1','''detect|Sensitive and selective detection|APPLICATION|sensitive selective gas detection
gases|target gases|ANALYTE|target gases unspecified
sensor|graphene gas sensors|DEVICE|generic graphene gas sensor
commercial|commercialization|APPLICATION|commercialization''')
    d.r('sensor','USED_FOR','detect',scope='BACKGROUND',mode='HYPOTHETICAL')
    d.s('S2','''sensor2|n-channel graphene gas sensors|DEVICE|n-channel graphene gas sensor
ultra|ultrasensitive|PERFORMANCE|high gas sensitivity
ndoped|n-doped graphene|MATERIAL|ethylene-amine n-doped graphene
amines|ethylene amines|MATERIAL|ethylene amines|dopant''')
    d.rs('''sensor2 USES_MATERIAL ndoped
sensor2 HAS_PERFORMANCE ultra
ndoped HAS_COMPONENT amines''')
    d.s('S3','''expose|exposure of the n-doped graphene to oxidizing gases|PROCESS|oxidizing gas exposure
ndoped3|n-doped graphene|MATERIAL|ethylene-amine n-doped graphene
oxidants|oxidizing gases|ANALYTE|oxidizing gases
no2|NO 2|ANALYTE|nitrogen dioxide
decrease|current decrease|PROPERTY|current decrease
number|number of amine functional groups|PROPERTY|amine functional-group count
groups|amine functional groups|MORPHOLOGY|amine functional groups
amines3|ethylene amines|MATERIAL|ethylene amines''')
    d.rs('''expose ACTS_ON ndoped3
ndoped3 HAS_PROPERTY decrease
amines3 HAS_PROPERTY number''')
    d.r('expose','CAUSES','decrease',note='Gas exposure causes a current decrease; PROPERTY endpoint is outside FACILITATES.')
    d.r('decrease','DEPENDS_ON','number',note='Явная зависимость current decrease от числа amine groups; не SAME и не HAS_COMPONENT.')
    d.s('S4','''deta_mat|Graphene doped with diethylenetriamine (DETA)|MATERIAL|DETA-doped graphene
deta|diethylenetriamine|MATERIAL|diethylenetriamine|dopant
deta_alias|DETA|MATERIAL|diethylenetriamine|dopant
response|highest response|PERFORMANCE|response
recovery|recovery|PERFORMANCE|recovery
stability|long-term sensing stability|PERFORMANCE|long-term sensing stability
no24|NO 2|ANALYTE|nitrogen dioxide|target_analyte|-1
lod|average detection limit|PERFORMANCE|average detection limit
interaction|attractive electrostatic interaction|MECHANISM|attractive electrostatic interaction
rich|electron-rich graphene|MATERIAL|electron-rich graphene
deficient|electron-deficient NO 2|ANALYTE|electron-deficient nitrogen dioxide''')
    d.rs('''deta_mat HAS_COMPONENT deta
deta_mat HAS_PERFORMANCE response
deta_mat HAS_PERFORMANCE recovery
deta_mat HAS_PERFORMANCE stability
deta_mat USED_FOR no24''',mode='COMPARED')
    d.r('deta_mat','HAS_PERFORMANCE','lod',q=[q('S4','0.83 parts per quadrillion (ppq, 10 –15 )','detection_limit',0.83,'ppq')])
    d.r('deta_mat','HAS_MECHANISM','interaction',note='Материал, а не названный DEVICE, является носителем объяснения. Требуется расширение domain HAS_MECHANISM.')
    d.s('S5','''calculation|first-principles calculation|TECHNOLOGY|first-principles calculation
adsorption|preferential adsorption|PROCESS|preferential NO2 adsorption
no25|NO 2|ANALYTE|nitrogen dioxide
ndoped5|n-doped graphene|MATERIAL|ethylene-amine n-doped graphene''')
    d.r('adsorption','ACTS_ON','ndoped5',mode='PROPOSED',q=[q('S5','first-principles calculation','support_method')])
    d.s('S6','''molecules|gas molecules|ANALYTE|gas molecules unspecified
channel|n-channel graphene|MATERIAL|n-channel graphene
impurities|charged impurities|MORPHOLOGY|charged impurities|charged_scattering_center
decrease6|current decrease|PROPERTY|current decrease
response6|excellent response|PERFORMANCE|response
oxidants6|oxidizing gases|ANALYTE|oxidizing gases
no26|NO 2|ANALYTE|nitrogen dioxide
so2|SO 2|ANALYTE|sulfur dioxide''')
    d.r('channel','HAS_MORPHOLOGY','impurities')
    d.r('impurities','INCREASES','decrease6',note='Charged impurities intensify current decrease; electronic structure → electrical property effect is uncovered.')
    d.r('channel','HAS_PERFORMANCE','response6',q=[q('S6','NO 2 or SO 2','analyte_scope')])
    d.s('S7','''nh3|NH 3|ANALYTE|ammonia|target_analyte|-1
interaction7|strong interaction|MECHANISM|strong NH3–DETA graphene interaction
deta7|DETA-doped graphene|MATERIAL|DETA-doped graphene
effects|combined effects of current increase by n-doping and mobility decrease by charged impurities|MECHANISM|combined opposing electronic effects
increase|current increase|PROPERTY|current increase
ndoping|n-doping|PROCESS|molecular n-doping
mobility|mobility decrease|PROPERTY|mobility decrease
impurities7|charged impurities|MORPHOLOGY|charged impurities|charged_scattering_center
no_response|completely no response|PERFORMANCE|NH3 response
nh37|NH 3|ANALYTE|ammonia|target_analyte|2''')
    d.r('deta7','HAS_PERFORMANCE','no_response',polarity='NEGATIVE',note='Explicit no response is a negative NH3 response assertion, not missing data.')
    d.r('sensor2','DETECTS','nh37',polarity='NEGATIVE',ss=['S2','S7'],note='DETA-doped configuration only; qualifier limits the generic n-channel platform.',q=[q('S7','DETA-doped graphene','material_configuration')])
    d.r('deta7','HAS_MECHANISM','interaction7',polarity='NEGATIVE',note='Absence of strong interaction is explicit; candidate domain extension, polarity retained separately.')
    d.data['unresolved'][-1]['candidates'][-1]['polarity']='NEGATIVE'
    d.r('deta7','HAS_MECHANISM','effects',note='The combined current-increase and mobility-decrease effects explain the NH3 nonresponse; frozen MATERIAL-domain gap, not an independently measured quantitative cancellation.')
    d.s('S8','''flex_sensor|flexible graphene sensor|DEVICE|flexible gate-free graphene sensor
flex|flexible|PROPERTY|flexibility
no28|NO 2|ANALYTE|nitrogen dioxide
plastic|plastic|MATERIAL|plastic substrate
stacks|vertical stacks of gate-electrode and gate-dielectric|DEVICE|vertical gate stacks
gate|gate-electrode|DEVICE|gate electrode
dielectric|gate-dielectric|DEVICE|gate dielectric
dopant|top-molecular dopant|MATERIAL|top molecular dopant''')
    d.rs('''flex_sensor HAS_PROPERTY flex
flex_sensor DETECTS no28
flex_sensor USES_MATERIAL plastic''')
    d.r('flex_sensor','HAS_COMPONENT','stacks',polarity='NEGATIVE',note='Explicit without vertical gate stacks.')
    d.s('S9','''gatefree|gate-free graphene gas sensors|DEVICE|flexible gate-free graphene sensor
doping9|nondestructive molecular n-doping|PROCESS|molecular n-doping
application|selective detection|APPLICATION|selective subppq NO2 detection
no29|NO 2|ANALYTE|nitrogen dioxide
mixture|gas mixture with reducing gases|OPERATING_CONDITION|gas mixture with reducing gases
reducing|reducing gases|ANALYTE|reducing gases''')
    d.r('gatefree','USED_FOR','application',mode='HYPOTHETICAL',q=[q('S9','subppq-level','concentration_regime'),q('S9','gas mixture with reducing gases','sample_condition')])
    d.r('gatefree','DETECTS','no29',mode='HYPOTHETICAL',q=[q('S9','subppq-level','concentration_regime')])
    d.identity('no2','nh3','DIFFERENT','Oxidizing NO2 and reducing NH3 are explicitly distinguished; negative NH3 result preserved.')
    d.identity('deta','amines','NARROWER','DETA is one named ethylene amine; the class is not SAME.')
    d.finish(['No NH3 response and no gate stacks are explicit negatives.',
              '0.83 ppq preserved without exponent conversion; NO2 and SO2 are distinct; theory and could be used are modal.',
              'Mechanistic/property dependencies outside 18 types are retained unresolved.'])


def D035():
    d=Record('D035')
    d.s('S1','''dft|density functional theory (DFT) calculations|TECHNOLOGY|density functional theory
mechanism|sensing mechanism|MECHANISM|gas sensing mechanism
co|CO|ANALYTE|carbon monoxide|target_analyte|-1
co2|CO 2|ANALYTE|carbon dioxide
no|NO|ANALYTE|nitric oxide|target_analyte|-1
no2|NO 2|ANALYTE|nitrogen dioxide
pure|pure|MATERIAL|pristine graphene
b|B@|MATERIAL|B-doped graphene
n|N@|MATERIAL|N-doped graphene|material|-1
bn|B–N@|MATERIAL|B,N-codoped graphene
surfaces|graphene surfaces|MORPHOLOGY|graphene surface''')
    d.s('S2','''energies|adsorption energies|PROPERTY|adsorption energy
gases|toxic gases|ANALYTE|CO/CO2/NO/NO2 gas group
co_2|CO|ANALYTE|carbon monoxide|target_analyte|-1
co2_2|CO 2|ANALYTE|carbon dioxide
no_2|NO|ANALYTE|nitric oxide|target_analyte|-1
no2_2|NO 2|ANALYTE|nitrogen dioxide
pure2|pure|MATERIAL|pristine graphene
doped|doped graphene|MATERIAL|doped graphene class
doping|doping|PROCESS|graphene doping
energy2|adsorption energy|PROPERTY|adsorption energy
selectivity|selectivity|PERFORMANCE|gas selectivity''')
    d.r('doping','IMPROVES','energy2',mode='COMPARED',q=[q('S2','calculated','epistemic_basis')])
    d.r('doping','IMPROVES','selectivity',mode='COMPARED',q=[q('S2','calculated','epistemic_basis')])
    for k in ['co_2','co2_2','no_2','no2_2']:d.r('gases','HAS_MEMBER',k)
    d.s('S3','''electronic|electronic properties|PROPERTY|electronic properties
bn3|B–N@graphene|MATERIAL|B,N-codoped graphene
pure3|pure|MATERIAL|pristine graphene
b3|B@|MATERIAL|B-doped graphene
n3|N@graphene|MATERIAL|N-doped graphene|material|2
adsorb|adsorbed|PROCESS|gas adsorption''')
    d.r('bn3','HAS_PROPERTY','electronic',mode='COMPARED',q=[q('S3','change significantly','change'),q('S3','compared to pure and B@ and N@graphene surfaces','comparison')])
    d.s('S4','''codoping|B–N codoping|PROCESS|B,N codoping
graphene|graphene|MATERIAL|graphene
sensitive|highly sensitive and selective|PERFORMANCE|high sensitivity and selectivity
sensor|semiconductor-based gas sensor|DEVICE|semiconductor-based gas sensor''')
    d.r('bn3','HAS_PERFORMANCE','sensitive',mode='HYPOTHETICAL',ss=['S3','S4'],note='Can be highly sensitive/selective is a DFT-based prospect, not fabricated sensor measurement.')
    d.r('sensor','USES_MATERIAL','bn3',mode='HYPOTHETICAL',ss=['S3','S4'])
    for k in ['pure','b','n','bn']:
        for gas in ['co','co2','no','no2']:
            d.r(k,'USED_FOR',gas,mode='PROPOSED',ss=['S1'],q=[q('S1','density functional theory (DFT) calculations','study_method')])
    d.identity('bn','b','DIFFERENT','B,N codoping is not B-only doping.')
    d.identity('bn','n','DIFFERENT','B,N codoping is not N-only doping.')
    d.identity('co','co2','DIFFERENT','CO and CO2 are distinct explicitly listed analytes.')
    d.identity('no','no2','DIFFERENT','NO and NO2 are distinct explicitly listed analytes.')
    d.finish(['DFT study, no numerical energy or device performance invented.',
              'Distinct pristine/B/N/B,N surfaces retained; no fabricated experiment inferred.'])


def D092():
    d=Record('D092')
    d.s('S1','''pristine|pristine|MATERIAL|pristine graphene
b|B-|MATERIAL|B-doped graphene
n|N-doped|MATERIAL|N-doped graphene
defective|defective graphenes|MATERIAL|defective graphene
co|CO|ANALYTE|carbon monoxide
no|NO|ANALYTE|nitric oxide|target_analyte|-1
no2|NO(2)|ANALYTE|nitrogen dioxide
nh3|NH(3)|ANALYTE|ammonia
dft|density functional computations|TECHNOLOGY|density functional theory
sensor|gas sensors|DEVICE|prospective graphene gas sensor''')
    for k in ['pristine','b','n','defective']:d.r('sensor','USES_MATERIAL',k,mode='HYPOTHETICAL')
    d.s('S2','''adduct|graphene-molecule adsorption adducts|MATERIAL|graphene–molecule adsorption adduct
structural|structural|PROPERTY|structural properties
electronic|electronic properties|PROPERTY|electronic properties
structure|graphene structure|MORPHOLOGY|graphene structure
configuration|molecular adsorption configuration|MORPHOLOGY|adsorption configuration''')
    d.rs('''adduct HAS_PROPERTY structural
adduct HAS_PROPERTY electronic''')
    for head in ['structural','electronic']:
        for tail in ['structure','configuration']:d.r(head,'DEPENDS_ON',tail,note='Явная зависимость свойств adduct от структуры и конфигурации; текущие predicates не выражают зависимость.')
    d.s('S3','''gases|four gas molecules|ANALYTE|CO/NO/NO2/NH3 gas group
adsorption|much stronger adsorption|PERFORMANCE|adsorption strength
doped|doped|MATERIAL|doped graphene class
defective3|defective graphenes|MATERIAL|defective graphene
pristine3|pristine graphene|MATERIAL|pristine graphene''')
    for k in ['doped','defective3']:d.r(k,'HAS_PERFORMANCE','adsorption',mode='COMPARED',q=[q('S3','than that on the pristine graphene','comparison')])
    d.s('S4','''defective4|defective graphene|MATERIAL|defective graphene
energy|highest adsorption energy|PROPERTY|adsorption energy
co4|CO|ANALYTE|carbon monoxide
no4|NO|ANALYTE|nitric oxide|target_analyte|-1
no24|NO(2)|ANALYTE|nitrogen dioxide
b4|B-doped graphene|MATERIAL|B-doped graphene
binding|tightest binding|PERFORMANCE|binding strength
nh34|NH(3)|ANALYTE|ammonia''')
    d.r('defective4','HAS_PROPERTY','energy',mode='COMPARED',q=[q('S4','CO, NO and NO(2) molecules','analyte_scope')])
    d.r('b4','HAS_PERFORMANCE','binding',mode='COMPARED',q=[q('S4','NH(3)','analyte_scope')])
    d.s('S5','''interaction|strong interactions|MECHANISM|gas–modified graphene interactions
modified|modified graphenes|MATERIAL|modified graphene class
changes|dramatic changes|PROCESS|electronic property change
electronic5|electronic properties|PROPERTY|electronic properties''')
    d.r('interaction','CAUSES','changes',note='Source says interactions induce electronic changes; causal structure is not HAS_PROPERTY.')
    d.s('S6','''sensor6|gas sensor|DEVICE|B-doped graphene gas sensor
b6|B-doped graphene|MATERIAL|B-doped graphene
sensitivity|sensitivity|PERFORMANCE|sensitivity
pristine6|pristine graphene|MATERIAL|pristine graphene''')
    d.r('sensor6','USES_MATERIAL','b6')
    d.r('sensor6','HAS_PERFORMANCE','sensitivity',mode='COMPARED',q=[q('S6','two orders of magnitude higher','relative_sensitivity'),q('S6','than that of pristine graphene','comparison')],note='Theoretical work context; not assigned to one particular gas without text.')
    d.s('S7','''sensitivity7|sensitivity|PERFORMANCE|sensitivity
sensor7|graphene-based chemical gas sensors|DEVICE|graphene chemical gas sensor
introduce|introducing the appropriate dopant or defect|PROCESS|dopant/defect introduction
dopant|dopant|MATERIAL|dopant unspecified
defect|defect|MORPHOLOGY|graphene defect''')
    d.r('introduce','IMPROVES','sensitivity7',mode='HYPOTHETICAL',note='Could be improved is prospective and does not define which dopant/defect is optimal.')
    for left,right in [('pristine','b'),('b','n'),('n','defective')]:d.identity(left,right,'DIFFERENT','Explicitly distinct graphene variants; do not normalize to generic graphene.')
    d.finish(['Theory context retained; no experimental temperature/LOD inferred.',
              'Adsorption comparisons preserve gas scope; sensitivity ratio not assigned to an unspecified target.'])


def D017():
    d=Record('D017')
    d.s('S1','''materials|Two-dimensional (2D) layered inorganic nanomaterials|MATERIAL|2D layered inorganic nanomaterials
dimension|Two-dimensional (2D) layered|MORPHOLOGY|2D layered morphology
electronic|unique electronic structures|MORPHOLOGY|electronic structure
properties|extraordinary physical and chemical properties|PROPERTY|physical/chemical property group
electronics|electronics|APPLICATION|electronics|application|-1
opto|optoelectronics|APPLICATION|optoelectronics
spin|spintronics|APPLICATION|spintronics
catalysts|catalysts|APPLICATION|catalysis
energy|energy generation and storage|APPLICATION|energy generation/storage
sensors|chemical sensors|DEVICE|chemical sensor''')
    d.rs('''materials HAS_MORPHOLOGY dimension
materials HAS_MORPHOLOGY electronic
materials HAS_PROPERTY properties
sensors USES_MATERIAL materials''',scope='REVIEW_BACKGROUND')
    for k in ['electronics','opto','spin','catalysts','energy']:d.r('materials','USED_FOR',k,scope='REVIEW_BACKGROUND')
    d.s('S2','''graphene|Graphene|MATERIAL|graphene
analogues|related layered inorganic analogues|MATERIAL|layered inorganic analogue class
application|gas-sensing applications|APPLICATION|gas sensing
area|large specific surface areas|PROPERTY|specific surface area
activity|strong surface activities|PROPERTY|surface activity''')
    for k in ['graphene','analogues']:
        d.r(k,'USED_FOR','application',scope='REVIEW_BACKGROUND')
        d.r(k,'HAS_PROPERTY','area',scope='REVIEW_BACKGROUND');d.r(k,'HAS_PROPERTY','activity',scope='REVIEW_BACKGROUND')
    d.s('S3','''materials3|2D layered inorganic materials|MATERIAL|2D layered inorganic nanomaterials
sensors3|gas sensors|DEVICE|gas sensor''')
    d.r('sensors3','USES_MATERIAL','materials3',scope='REVIEW_SCOPE')
    d.s('S4','''mechanisms|gas-sensing mechanisms|MECHANISM|gas sensing mechanisms unspecified
devices|gas-sensing devices|DEVICE|gas sensor''')
    d.r('devices','HAS_MECHANISM','mechanisms',scope='REVIEW_SCOPE',note='Review discusses mechanisms generically; no specific mechanism invented.')
    d.s('S5','''parameters|basic parameters|PROPERTY|gas sensor parameters unspecified
influences|influence factors|OTHER|gas sensor influence factors unspecified
sensors5|gas sensors|DEVICE|gas sensor
performance|performance|PERFORMANCE|gas sensing performance''')
    d.rs('''sensors5 HAS_PROPERTY parameters
sensors5 HAS_PERFORMANCE performance''',scope='REVIEW_SCOPE')
    d.s('S6','''application6|gas-sensing applications|APPLICATION|gas sensing
graphene6|graphene|MATERIAL|graphene|material|-1
go|graphene oxide|MATERIAL|graphene oxide|material|-1
go_alias|GO|MATERIAL|graphene oxide|material_alias|-1
rgo|reduced graphene oxide|MATERIAL|reduced graphene oxide
rgo_alias|rGO|MATERIAL|reduced graphene oxide|material_alias|-1
functional|functionalized GO or rGO|MATERIAL|functionalized GO/rGO class
tmd|transition metal dichalcogenides|MATERIAL|transition metal dichalcogenides
iii|layered III-VI semiconductors|MATERIAL|layered III-VI semiconductors
oxides|layered metal oxides|MATERIAL|layered metal oxides
phosphorene|phosphorene|MATERIAL|phosphorene
hbn|hexagonal boron nitride|MATERIAL|hexagonal boron nitride''')
    for k in ['graphene6','go','rgo','functional','tmd','iii','oxides','phosphorene','hbn']:d.r(k,'USED_FOR','application6',scope='REVIEW_SCOPE')
    d.s('S7','''materials7|layered inorganic materials|MATERIAL|2D layered inorganic nanomaterials
application7|gas-sensing applications|APPLICATION|gas sensing''')
    d.r('materials7','USED_FOR','application7',scope='REVIEW_OUTLOOK',mode='HYPOTHETICAL')
    for left,right in [('graphene','go'),('go','rgo'),('rgo','functional')]:d.identity(left,right,'DIFFERENT','Distinct material forms listed by the review; functionalized class not merged with unmodified material.')
    d.finish(['Review scope is explicit; no generic topics converted into measured experimental findings.',
              'Graphene, GO, rGO, functionalized materials and analogues remain distinct.'])


def D038():
    d=Record('D038')
    d.s('S1','''hybrid|Graphene/metal oxide-based materials|MATERIAL|graphene/metal oxide hybrid
application|gas sensing applications|APPLICATION|gas sensing
performance|enhanced sensing performance|PERFORMANCE|sensing performance
synergy|synergetic effects|MECHANISM|graphene–oxide synergy''')
    d.rs('''hybrid USED_FOR application
hybrid HAS_PERFORMANCE performance''',scope='REVIEW_BACKGROUND')
    d.r('hybrid','HAS_MECHANISM','synergy',note='Материал является носителем заявленной synergy; HAS_MECHANISM domain сейчас DEVICE.')
    d.s('S2','''oxides|metal oxides|MATERIAL|metal oxide class
sno2|SnO₂|MATERIAL|tin dioxide
zno|ZnO|MATERIAL|zinc oxide
wo3|WO₃|MATERIAL|tungsten trioxide
graphene|graphene|MATERIAL|graphene
hybridize|hybridized with graphene|PROCESS|graphene–oxide hybridization
properties|gas sensing properties|PERFORMANCE|sensing performance''')
    for k in ['sno2','zno','wo3']:d.identity(k,'oxides','NARROWER','Named metal oxide within an explicit class, not equivalent to the entire class.')
    d.rs('''hybrid HAS_COMPONENT oxides
hybrid HAS_COMPONENT graphene''',ss=['S1','S2'],scope='REVIEW_BACKGROUND')
    d.r('hybridize','IMPROVES','properties',mode='PROPOSED',scope='REVIEW_BACKGROUND')
    d.s('S3','''sensors|graphene/metal oxide nanohybrid- based gas sensors|DEVICE|graphene/oxide nanohybrid gas sensor
sensitivity|insufficient sensitivity|PERFORMANCE|insufficient sensitivity
response|response rate|PERFORMANCE|insufficient response rate
recovery|long recovery time|PERFORMANCE|long recovery time
application3|practical application|APPLICATION|practical gas sensing''')
    for k in ['sensitivity','response','recovery']:d.r('sensors','HAS_PERFORMANCE',k,scope='REVIEW_LIMITATION',q=[q('S3','in some cases','scope_limit')])
    d.s('S4','''synthesis|controllable synthesis|PROCESS|controllable 3D hybrid synthesis
architecture|3D graphene/metal oxides architectures|MATERIAL|3D graphene/metal oxide hybrid
three|3D|MORPHOLOGY|three-dimensional morphology
area|large surface area|PROPERTY|surface area
structure|well-organized structure|MORPHOLOGY|well-organized structure
adsorb|gas adsorption/diffusion|PROCESS|gas adsorption/diffusion
films|sensing films|DEVICE|sensing film''')
    d.rs('''architecture FABRICATED_BY synthesis
architecture HAS_MORPHOLOGY three
architecture HAS_MORPHOLOGY structure
architecture HAS_PROPERTY area''',scope='REVIEW_BACKGROUND')
    d.r('architecture','FACILITATES','adsorb',scope='REVIEW_BACKGROUND',q=[q('S4','on sensing films','process_location')])
    d.s('S5','''synth5|synthesis|PROCESS|3D hybrid synthesis
assembly|assembly|PROCESS|3D hybrid assembly
hybrid5|3D architectured graphene/metal oxide hybrids|MATERIAL|3D graphene/metal oxide hybrid
application5|gas sensing|APPLICATION|gas sensing''')
    d.rs('''hybrid5 FABRICATED_BY synth5
hybrid5 FABRICATED_BY assembly
hybrid5 USED_FOR application5''',scope='REVIEW_SCOPE')
    d.finish(['Limitations have in some cases scope; no universal failure claim or invented numeric recovery time.',
              'Review-level application and synthesis claims kept separate from experimental results.'])


def D026():
    d=Record('D026')
    d.s('S1','''sensitivity|high sensitivity|PERFORMANCE|high sensitivity
sensor|solid-state gas sensors|DEVICE|solid-state gas sensor
agents|chemical agents|ANALYTE|chemical agents unspecified
detection|precise detection|APPLICATION|precise chemical-agent detection''')
    d.r('sensor','USED_FOR','detection',mode='HYPOTHETICAL',scope='BACKGROUND')
    d.s('S2','''vocs|volatile organic compounds|ANALYTE|volatile organic compounds
vocs_alias|VOCs|ANALYTE|volatile organic compounds
ppb|parts per billion (ppb) level|OPERATING_CONDITION|ppb concentration regime
diagnosis|early diagnosis of diseases|APPLICATION|early disease diagnosis''')
    d.s('S3','''noise|low electrical noise|PROPERTY|low electrical noise
signal|strong signal|PERFORMANCE|strong signal
materials|existing sensor materials|MATERIAL|existing sensor materials unspecified''')
    d.r('materials','MEETS_REQUIREMENT','noise',polarity='NEGATIVE',note='Cannot simultaneously meet low noise and strong signal: group negation must not become two independent failures.')
    # Preserve the joint negation as one candidate with an explicit note.
    d.data['unresolved'][-1]['candidates'][-1]['polarity']='NEGATIVE'
    d.data['unresolved'][-1]['candidates'][-1]['joint_scope']='low electrical noise AND strong signal; not independent negations'
    d.s('S4','''mxene|2D metal carbide MXenes|MATERIAL|2D metal carbide MXene
two|2D|MORPHOLOGY|two-dimensional morphology
conductivity|high metallic conductivity|PROPERTY|metallic conductivity
noise4|low noise|PROPERTY|low electrical noise
surface|fully functionalized surface|MORPHOLOGY|fully functionalized surface
signal4|strong signal|PERFORMANCE|strong signal
sensitivity4|sensitivity|PERFORMANCE|sensitivity
semiconductor|conventional semiconductor channel materials|MATERIAL|conventional semiconductor channel material''')
    d.rs('''mxene HAS_MORPHOLOGY two
mxene HAS_MORPHOLOGY surface
mxene HAS_PROPERTY conductivity
mxene HAS_PROPERTY noise4
mxene HAS_PERFORMANCE signal4''')
    d.r('mxene','HAS_PERFORMANCE','sensitivity4',mode='COMPARED',q=[q('S4','greatly outperform','comparison_direction'),q('S4','conventional semiconductor channel materials','comparison_material')])
    d.s('S5','''sensor5|Ti3C2Tx MXene gas sensors|DEVICE|Ti3C2Tx MXene gas sensor
ti|Ti3C2Tx MXene|MATERIAL|Ti3C2Tx MXene
lod|very low limit of detection|PERFORMANCE|detection limit
vocs5|VOC gases|ANALYTE|volatile organic compounds
rt|room temperature|OPERATING_CONDITION|room temperature''')
    d.rs('''sensor5 USES_MATERIAL ti
sensor5 DETECTS vocs5''')
    d.r('sensor5','HAS_PERFORMANCE','lod',q=[q('S5','50–100 ppb','detection_limit_range',[50,100],'ppb'),q('S5','room temperature','temperature')])
    d.s('S6','''noise6|extremely low noise|PROPERTY|low electrical noise
snr|signal-to-noise ratio|PERFORMANCE|signal-to-noise ratio
other|other 2D materials|MATERIAL|other 2D materials
best|best sensors known|DEVICE|comparison best sensors unspecified''')
    d.r('sensor5','HAS_PERFORMANCE','snr',mode='COMPARED',q=[q('S6','2 orders of magnitude higher','SNR_ratio'),q('S6','other 2D materials','comparison_material')],ss=['S5','S6'])
    d.r('noise6','EXPLAINS','snr',note='Low noise led to SNR advantage; PROPERTY → PERFORMANCE causal effect cannot be replaced by HAS_PROPERTY.')
    d.s('S7','''channel|highly functionalized metallic sensing channels|DEVICE|functionalized metallic sensing channel
sensor7|highly sensitive sensors|DEVICE|prospective highly sensitive sensor''')
    d.r('sensor7','HAS_COMPONENT','channel',mode='HYPOTHETICAL',scope='OUTLOOK')
    d.finish(['Joint cannot-meet statement preserved as a single unresolved joint constraint; no false two-way negation.',
              'VOC class not narrowed to a named organic molecule; 50–100 ppb and room temperature attached to LOD only.',
              'SNR 2 orders comparison is to other 2D materials, not a numeric absolute SNR.'])


def D024():
    d=Record('D024')
    d.s('S1','''permeability|permeability|PROPERTY|permeability
selectivity|selectivity|PERFORMANCE|gas separation selectivity
sheets|graphene sheets|MATERIAL|porous graphene sheet
pores|designed subnanometer pores|MORPHOLOGY|subnanometer pore
dft|first principles density functional theory calculations|TECHNOLOGY|first-principles DFT''')
    d.rs('''sheets HAS_PROPERTY permeability
sheets HAS_PERFORMANCE selectivity
sheets HAS_MORPHOLOGY pores''')
    d.s('S2','''selectivity2|high selectivity|PERFORMANCE|H2/CH4 selectivity
h2|H(2)|ANALYTE|hydrogen|permeating_gas|-1
ch4|CH(4)|ANALYTE|methane
permeance|high H(2) permeance|PERFORMANCE|H2 permeance
nitrogen|nitrogen-functionalized pore|MORPHOLOGY|nitrogen-functionalized pore''')
    d.r('sheets','HAS_PERFORMANCE','selectivity2',q=[q('S2','10(8)','selectivity_order'),q('S2','H(2)/CH(4)','gas_pair'),q('S2','nitrogen-functionalized pore','pore_configuration')],ss=['S1','S2'])
    d.r('sheets','HAS_PERFORMANCE','permeance',q=[q('S2','nitrogen-functionalized pore','pore_configuration')],ss=['S1','S2'])
    d.s('S3','''selectivity3|extremely high selectivity|PERFORMANCE|H2/CH4 selectivity
h2_3|H(2)|ANALYTE|hydrogen|permeating_gas|-1
ch4_3|CH(4)|ANALYTE|methane|restricted_gas|-1
hydrogenpore|all-hydrogen passivated pore|MORPHOLOGY|all-hydrogen-passivated pore
width|small width|PROPERTY|pore width
barrier|formidable barrier|PROPERTY|CH4 permeation barrier''')
    d.r('sheets','HAS_PERFORMANCE','selectivity3',q=[q('S3','10(23)','selectivity_order'),q('S3','H(2)/CH(4)','gas_pair'),q('S3','all-hydrogen passivated pore','pore_configuration')],ss=['S1','S3'])
    d.r('hydrogenpore','HAS_PROPERTY','width',q=[q('S3','2.5 A','pore_width',2.5,'A')],note='MORPHOLOGY → PROPERTY endpoint gap; keep source unit A without silent Angstrom normalization.')
    d.r('sheets','HAS_PROPERTY','barrier',q=[q('S3','1.6 eV','CH4_barrier',1.6,'eV'),q('S3','0.22 eV','H2_barrier',0.22,'eV'),q('S3','all-hydrogen passivated pore','pore_configuration')],ss=['S1','S3'])
    d.s('S4','''pores4|pores|MORPHOLOGY|graphene pore class
polymer|polymer|MATERIAL|polymer membrane material
silica|silica membranes|DEVICE|silica membrane
solubility|bulk solubility|PROPERTY|bulk solubility
diffusivity|diffusivity|PROPERTY|diffusivity
transport|transport of gas molecules|PROCESS|gas transport''')
    d.r('solubility','DOMINATES','transport',note='Transport dominated by bulk solubility/diffusivity; PROPERTY → PROCESS dominance is not FACILITATES.')
    d.r('diffusivity','DOMINATES','transport',note='Transport dominated by bulk solubility/diffusivity; PROPERTY → PROCESS dominance is not FACILITATES.')
    d.s('S5','''beams|electron beams|TECHNOLOGY|electron-beam pore fabrication
bottomup|bottom-up synthesis|PROCESS|bottom-up synthesis
create|create pores in graphene|PROCESS|graphene pore creation
graphene5|graphene|MATERIAL|graphene|material|-1
nanopores|variable-sized, graphene nanopores|MORPHOLOGY|variable-size graphene nanopores
selectivity5|selectivity|PERFORMANCE|gas separation selectivity
diffusivity5|molecular diffusivity|PROPERTY|molecular diffusivity''')
    d.r('create','ACTS_ON','graphene5',mode='PROPOSED',q=[q('S5','electron beams or bottom-up synthesis','fabrication_techniques')])
    d.r('create','OPTIMIZES','graphene5',mode='HYPOTHETICAL',note='May be possible to engineer pores to tune selectivity; not demonstrated optimal values.')
    d.s('S6','''sheets6|porous graphene sheets|MATERIAL|porous graphene sheet
membrane|one-atom-thin, highly efficient, and highly selective membranes|DEVICE|porous graphene gas separation membrane
thin|one-atom-thin|MORPHOLOGY|one-atom-thin morphology
efficient|highly efficient|PERFORMANCE|high efficiency
selective|highly selective|PERFORMANCE|high selectivity
separation|gas separation|APPLICATION|gas separation''')
    d.rs('''sheets6 FUNCTIONS_AS membrane
membrane HAS_MORPHOLOGY thin
membrane HAS_PERFORMANCE efficient
membrane HAS_PERFORMANCE selective
membrane USED_FOR separation''',mode='PROPOSED')
    d.s('S7','''pore7|pore|MORPHOLOGY|graphene pore class
sequestration|carbon sequestration|APPLICATION|carbon sequestration
fuel|fuel cells|DEVICE|fuel cell
sensors7|gas sensors|DEVICE|gas sensor''')
    d.r('membrane','USED_FOR','sequestration',mode='HYPOTHETICAL',scope='OUTLOOK',ss=['S6','S7'])
    d.r('sheets6','USED_FOR','fuel',mode='HYPOTHETICAL',scope='OUTLOOK',ss=['S6','S7'],note='Prospective application to fuel cells; material-to-device use is outside allowed USED_FOR tails, and a physical component relation is not explicitly asserted.')
    d.r('sheets6','USED_FOR','sensors7',mode='HYPOTHETICAL',scope='OUTLOOK',ss=['S6','S7'],note='Prospective application to gas sensors; no separately fabricated component is asserted.')
    d.identity('nitrogen','hydrogenpore','DIFFERENT','Two pore functionalization configurations; selectivity orders and barriers cannot be merged.')
    d.finish(['Theoretical 10(8)/10(23) selectivity values remain literal; no invented experimental separation.',
              'Barrier values preserve H2/CH4 attachment. A remains source unit; nitrogen and H passivation distinct.',
              'Gas sensor/fuel-cell use is hypothetical outlook, not measured device performance.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('codes',nargs='*');args=parser.parse_args()
    for code in args.codes or ['D004','D060','D078','D035','D092','D017','D038','D026','D024']:globals()[code]()
