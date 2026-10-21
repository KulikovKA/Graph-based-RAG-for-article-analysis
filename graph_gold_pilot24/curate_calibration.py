"""Calibration curation under the frozen schema; no ontology modifications."""
import argparse
from campaign_helpers import Record,q


def D018():
    d=Record('D018')
    d.s('S1','''meso|Reduced graphene oxide (rGO)-conjugated Cu(2)O nanowire mesocrystals|MATERIAL|rGO-conjugated Cu2O nanowire mesocrystal
rgo|Reduced graphene oxide|MATERIAL|reduced graphene oxide
rgo_alias|rGO|MATERIAL|reduced graphene oxide
cu2o|Cu(2)O|MATERIAL|Cu2O
crystal|nonclassical crystallization|PROCESS|nonclassical crystallization
go|GO|MATERIAL|graphene oxide precursor|precursor|2
anisidine|o-anisidine|MATERIAL|o-anisidine|synthesis_reagent
hydro|hydrothermal conditions|OPERATING_CONDITION|hydrothermal conditions''')
    d.rs('''meso HAS_COMPONENT rgo
meso HAS_COMPONENT cu2o''')
    d.r('meso','FABRICATED_BY','crystal',q=[q('S1','hydrothermal conditions','synthesis_conditions'),q('S1','GO and o-anisidine','reagents')])
    d.s('S2','''meso2|mesocrystals|MATERIAL|rGO-conjugated Cu2O nanowire mesocrystal
wires|highly anisotropic nanowires|MATERIAL|anisotropic nanowire building blocks
octa|distinct octahedral morphology|MORPHOLOGY|octahedral morphology
faces|eight {111} equivalent crystal faces|MORPHOLOGY|eight equivalent {111} faces''')
    d.rs('''meso2 HAS_COMPONENT wires
meso2 HAS_MORPHOLOGY octa
meso2 HAS_MORPHOLOGY faces''')
    d.s('S3','''mechanisms|mechanisms underlying the sequential formation|MECHANISM|sequential mesocrystal formation mechanism
agglomeration|agglomeration of amorphous spherical Cu(2)O nanoparticles|PROCESS|Cu2O nanoparticle agglomeration
go3|GO|MATERIAL|graphene oxide precursor|precursor|-1
amorphous|amorphous spherical Cu(2)O nanoparticles|MATERIAL|amorphous spherical Cu2O nanoparticles
ion|conventional ion-by-ion growth|PROCESS|ion-by-ion growth
particle|particle-mediated crystallization|PROCESS|particle-mediated crystallization
evolution|evolution of the amorphous microspheres into hierarchical structure|PROCESS|microsphere hierarchical evolution
spheres|amorphous microspheres|MATERIAL|amorphous microspheres
hierarchical|hierarchical structure|MORPHOLOGY|hierarchical structure
transformation|mesoscale transformation|PROCESS|mesoscale transformation
ripening|Ostwald ripening|PROCESS|Ostwald ripening
growth|growth of the nanowire building blocks|PROCESS|nanowire growth
organization|large-scale self-organization of the mesocrystals|PROCESS|mesocrystal self-organization
reduction|reduction of GO|PROCESS|GO reduction
highgo|high GO concentration|OPERATING_CONDITION|high GO concentration
hybrid|integrated hybrid architecture|MATERIAL|3D framework/2D rGO integrated hybrid
framework|porous three-dimensional (3D) framework structures|MORPHOLOGY|porous 3D framework
sheets|two-dimensional (2D) rGO sheets|MATERIAL|2D rGO sheet''')
    d.r('go3','FACILITATES','agglomeration',q=[q('S3','at the initial stage','sequence_stage')])
    d.r('ripening','FACILITATES','growth',q=[q('S3','responsible for','source_causal_wording')])
    d.r('reduction','ACTS_ON','go3',q=[q('S3','at high GO concentration','condition')])
    d.rs('''hybrid HAS_MORPHOLOGY framework
hybrid HAS_COMPONENT sheets
evolution ACTS_ON spheres''')
    d.r('hybrid','FABRICATED_BY','organization',q=[q('S3','occur simultaneously','temporal_relation'),q('S3','reduction of GO','cooccurring_process')])
    d.r('ion','TRANSITIONS_TO','particle',note='Переход growth mechanism ion-by-ion → particle-mediated; frozen types do not encode transition. Agglomeration is the stated preceding trigger, not the mechanism being transformed.')
    d.r('meso2','HAS_MECHANISM','mechanisms',note='Formation mechanism is attached to a MATERIAL rather than a DEVICE; frozen domain gap.')
    d.s('S4','''super|"super-mesocrystals"|MATERIAL|super-mesocrystal
attachment|3D oriented attachment of mesocrystals|PROCESS|3D oriented mesocrystal attachment
polyhedrons|voided Sierpinski polyhedrons|MORPHOLOGY|voided Sierpinski polyhedron''')
    d.r('super','FABRICATED_BY','attachment',mode='PROPOSED',q=[q('S4','judging from the voided Sierpinski polyhedrons observed','support_basis')])
    d.r('super','HAS_MORPHOLOGY','polyhedrons')
    d.s('S5','''architecture|interior nanowire architecture|MORPHOLOGY|interior nanowire architecture
variation|careful variation of growth conditions|PROCESS|growth-condition variation''')
    d.r('variation','CONTROLS','architecture',mode='HYPOTHETICAL',note='Kinetic control of interior architecture; PROCESS → MORPHOLOGY control not expressible as OPTIMIZES DEVICE/MATERIAL.')
    d.s('S6','''area|high specific surface area|PROPERTY|specific surface area
conductivity|improved conductivity|PROPERTY|conductivity
meso6|rGO-Cu(2)O mesocrystals|MATERIAL|rGO-conjugated Cu2O nanowire mesocrystal
sensitivity|higher sensitivity|PERFORMANCE|NO2 sensitivity
no2|NO(2)|ANALYTE|nitrogen dioxide
rt|room temperature|OPERATING_CONDITION|room temperature
standalone|standalone systems of Cu(2)O nanowires networks and rGO sheets|MATERIAL|standalone Cu2O networks/rGO sheet comparison group''')
    d.rs('''meso6 HAS_PROPERTY area
meso6 HAS_PROPERTY conductivity
meso6 USED_FOR no2''')
    d.r('meso6','HAS_PERFORMANCE','sensitivity',mode='COMPARED',q=[q('S6','room temperature','temperature'),q('S6','standalone systems of Cu(2)O nanowires networks and rGO sheets','comparison')])
    d.s('S7','''meso7|rGO-Cu(2)O mesocrystal|MATERIAL|rGO-conjugated Cu2O nanowire mesocrystal
sensors|ultrasensitive environmental sensors|DEVICE|prospective ultrasensitive environmental sensor''')
    d.r('sensors','USES_MATERIAL','meso7',mode='HYPOTHETICAL',scope='OUTLOOK')
    d.identity('go','rgo','DIFFERENT','GO precursor and reduced product are chemically distinct; reduction is not SAME.')
    d.finish(['Cu2O preserved, not CuO. Eight {111} faces and hydrothermal/reagent conditions retained.',
              'Formation sequence, simultaneous processes and morphology changes remain in candidates when frozen schema cannot express them.',
              'Room temperature belongs to NO2 comparison; no numeric sensitivity/LOD is invented.'])


def D050():
    d=Record('D050')
    d.s('S1','''sensor|flexible room temperature NO2 gas sensor|DEVICE|flexible CNT/reduced graphene NO2 sensor
flex|flexible|PROPERTY|flexibility
rt|room temperature|OPERATING_CONDITION|room temperature
no2|NO2|ANALYTE|nitrogen dioxide
film|vertical carbon nanotubes (CNTs)/reduced graphene hybrid film|MATERIAL|CNT/reduced graphene hybrid film
cnt|carbon nanotubes|MATERIAL|carbon nanotubes
cnt_alias|CNTs|MATERIAL|carbon nanotubes
substrate|polyimide substrate|DEVICE|polyimide substrate
polyimide|polyimide|MATERIAL|polyimide''')
    d.rs('''sensor HAS_PROPERTY flex
sensor USES_MATERIAL film
sensor HAS_COMPONENT substrate
substrate USES_MATERIAL polyimide
film HAS_COMPONENT cnt''')
    d.r('sensor','DETECTS','no2',q=[q('S1','room temperature','temperature')])
    d.s('S2','''reduced|reduced graphene film|MATERIAL|reduced graphene film
response|negligible sensor response|PERFORMANCE|negligible NO2 response
transition|abnormal N–P transitions|MECHANISM|abnormal N–P transition
injection|initial NO2 injection|PROCESS|initial NO2 injection
no22|NO2|ANALYTE|nitrogen dioxide''')
    d.r('reduced','HAS_PERFORMANCE','response',q=[q('S2','alone','material_configuration'),q('S2','initial NO2 injection','exposure_stage')])
    d.r('reduced','HAS_MECHANISM','transition',note='Material N–P transition and initial-injection scope cannot be represented by DEVICE-only HAS_MECHANISM.')
    d.s('S3','''hybrid3|hybrid film|MATERIAL|CNT/reduced graphene hybrid film
growth|growth of a vertically aligned CNT array|PROCESS|vertical CNT array growth
array|vertically aligned CNT array|MATERIAL|vertical CNT array
cnt3|CNTs|MATERIAL|carbon nanotubes
length|20 μm in length|PROPERTY|CNT length
reduced3|reduced graphene film|MATERIAL|reduced graphene film
sensitivity|remarkably enhanced sensitivities|PERFORMANCE|NO2 sensitivity
weak|weak N–P transitions|MECHANISM|weak N–P transition''')
    d.rs('''hybrid3 FABRICATED_BY growth
hybrid3 HAS_COMPONENT array
hybrid3 HAS_COMPONENT reduced3
array HAS_COMPONENT cnt3''')
    d.r('cnt3','HAS_PROPERTY','length',q=[q('S3','20 μm','length',20,'μm')])
    d.r('hybrid3','HAS_PERFORMANCE','sensitivity',mode='COMPARED',note='Enhanced relative to standalone film context; no numeric gain given.')
    d.r('hybrid3','HAS_MECHANISM','weak',note='Weak N–P transitions observed in hybrid material; frozen HAS_MECHANISM domain excludes MATERIAL.')
    d.s('S4','''increase|increase in sensitivity|PERFORMANCE|hybrid sensitivity increase
array4|CNT arrays|MATERIAL|vertical CNT array
high|high sensitivity|PERFORMANCE|CNT array sensitivity''')
    d.r('array4','HAS_PERFORMANCE','high')
    d.r('high','EXPLAINS','increase',note='Attribution to CNT-array sensitivity is a PERFORMANCE → PERFORMANCE explanatory link, absent from frozen schema.')
    d.s('S5','''flex5|outstanding flexibility|PROPERTY|flexibility
reduced5|reduced graphene films|MATERIAL|reduced graphene film
stable|stable sensing performances|PERFORMANCE|stable sensing performance
devices|devices|DEVICE|flexible CNT/reduced graphene NO2 sensor
stress|extreme bending stress|OPERATING_CONDITION|extreme bending stress''')
    d.r('reduced5','HAS_PROPERTY','flex5')
    d.r('devices','HAS_PERFORMANCE','stable',q=[q('S5','extreme bending stress','mechanical_condition')])
    d.r('flex5','EXPLAINS','stable',note='Flexibility ensures stable performance under bending; property-to-performance explanation is uncovered.')
    d.finish(['Reduced graphene wording is preserved without automatically equating it to chemically defined rGO.',
              'Negligible response is low magnitude, not categorical non-detection. Initial N–P transitions and bending stability have separate conditions.'])


def D029():
    d=Record('D029')
    d.s('S1','''graphene|Graphene|MATERIAL|graphene
cheap|cheap|PROPERTY|low cost
sensitivity|high sensitivity|PERFORMANCE|high sensitivity
robust|robust towards contamination|PERFORMANCE|contamination robustness
noise|low noise|PROPERTY|low noise
power|low power consumption|PROPERTY|low power consumption
sensor|gas sensors|DEVICE|prospective graphene gas sensor
surface|large surface|PROPERTY|large surface area
mobility|high mobility|PROPERTY|high mobility
stability|long-term stability|PERFORMANCE|long-term stability''')
    for k in ['surface','mobility']:d.r('graphene','HAS_PROPERTY',k,scope='BACKGROUND')
    d.r('graphene','HAS_PERFORMANCE','stability',scope='BACKGROUND')
    for k in ['sensitivity','robust']:d.r('sensor','HAS_PERFORMANCE',k,mode='HYPOTHETICAL',scope='BACKGROUND_REQUIREMENT')
    for k in ['cheap','noise','power']:d.r('sensor','HAS_PROPERTY',k,mode='HYPOTHETICAL',scope='BACKGROUND_REQUIREMENT')
    d.s('S2','''printing|Inkjet printing|PROCESS|inkjet printing
cheap2|cheap|PROPERTY|low cost
manufacture|additive manufacturing method|TECHNOLOGY|additive manufacturing
deposit|fast, relatively precise and contactless deposition|PROCESS|fast precise contactless deposition
film|graphene films|MATERIAL|graphene film
substrate|thin substrates|DEVICE|thin substrate''')
    d.r('printing','HAS_PROPERTY','cheap2',scope='BACKGROUND')
    d.r('film','FABRICATED_BY','printing',mode='PROPOSED',q=[q('S2','thin substrates','deposition_substrate')],scope='BACKGROUND')
    d.s('S3','''sensitivity3|sensitivity|PERFORMANCE|gas sensitivity
sensor3|graphene-based chemiresistor gas sensors|DEVICE|inkjet-printed graphene chemiresistor
printing3|inkjet printing|PROCESS|inkjet printing
graphene3|graphene|MATERIAL|graphene|material|2
concentrations|different concentrations of graphene in the inks|OPERATING_CONDITION|graphene ink concentration variation
inks|inks|MATERIAL|graphene ink''')
    d.rs('''sensor3 FABRICATED_BY printing3
sensor3 USES_MATERIAL graphene3
sensor3 HAS_PERFORMANCE sensitivity3
inks HAS_COMPONENT graphene3''')
    d.s('S4','''samples|Samples|DEVICE|inkjet-printed graphene chemiresistor
response|response|PERFORMANCE|gas sensor response
humidity|humidity|ANALYTE|humidity stimulus|environmental_stimulus
no2|nitrogen dioxide|ANALYTE|nitrogen dioxide
nh3|ammonia|ANALYTE|ammonia''')
    d.r('samples','HAS_PERFORMANCE','response',q=[q('S4','humidity, nitrogen dioxide, and ammonia','tested_stimuli')])
    d.s('S5','''tuning|tuning the layer thickness|PROCESS|layer thickness tuning
thickness|layer thickness|PROPERTY|sensing layer thickness
homogeneity|good film homogeneity|PROPERTY|film homogeneity
sensitivity5|sensitivity|PERFORMANCE|gas sensitivity
sensor5|sensor|DEVICE|inkjet-printed graphene chemiresistor''')
    d.r('tuning','IMPROVES','sensitivity5',mode='PROPOSED',note='Aim maximize sensitivity; no optimal thickness or quantitative sensitivity is supplied.')
    d.r('homogeneity','EXPLAINS','sensitivity5',note='Importance of film homogeneity for sensitivity is a PROPERTY → PERFORMANCE effect, not a measured numeric relation.')
    d.identity('no2','nh3','DIFFERENT','Two named measured gas stimuli; no selectivity ordering supplied.')
    d.finish(['Background market requirements are hypothetical targets, not measured properties of the study sensors.',
              'Only response characterization is stated, so no invented successful DETECTS threshold for each stimulus.',
              'Humidity is a tested stimulus, not device material; ink concentration and thickness values remain unspecified.'])


def D042():
    d=Record('D042')
    d.s('S1','''agnr|armchair graphene nanoribbon|MATERIAL|armchair graphene nanoribbon
alias|AGNR|MATERIAL|armchair graphene nanoribbon
materials|sensor materials|MATERIAL|four AGNR sensor-material group
tool|Atomistic ToolKit Virtual NanoLab (ATK-VNL)|TECHNOLOGY|ATK-VNL
co|carbon monoxide|ANALYTE|carbon monoxide
coalias|CO|ANALYTE|carbon monoxide|chemical_alias|-1
co2|carbon dioxide|ANALYTE|carbon dioxide
co2alias|CO2|ANALYTE|carbon dioxide''')
    for gas in ['co','co2']:d.r('materials','USED_FOR',gas,q=[q('S1','Atomistic ToolKit Virtual NanoLab (ATK-VNL)','computational_tool')],scope='COMPUTATIONAL_RESULT')
    d.s('S2','''passivate|passivating AGNR|PROCESS|AGNR passivation
performance|sensing performance|PERFORMANCE|sensing performance
hydrogen|hydrogen|MATERIAL|hydrogen passivant|passivant
nitrogen|nitrogen|MATERIAL|nitrogen passivant|passivant
h|H-AGNR|MATERIAL|H-passivated AGNR
n|N-AGNR|MATERIAL|N-passivated AGNR''')
    d.r('h','FABRICATED_BY','passivate',q=[q('S2','hydrogen','passivant')])
    d.r('n','FABRICATED_BY','passivate',q=[q('S2','nitrogen','passivant')])
    d.s('S3','''changes|significant changes|PROCESS|significant adsorption-parameter change
parameters|adsorption parameters|PROPERTY|adsorption parameters
co3|CO|ANALYTE|carbon monoxide|target_analyte|-1
co23|CO2|ANALYTE|carbon dioxide
h3|H-AGNR|MATERIAL|H-passivated AGNR
n3|N-AGNR|MATERIAL|N-passivated AGNR''')
    d.r('passivate','CAUSES','changes',polarity='NEGATIVE',ss=['S2','S3'],note='No significant changes is the explicit result; not a blanket no adsorption/no sensing claim.')
    d.s('S4','''energy|adsorption energies|PROPERTY|adsorption energy|metric|-1
h4|H-AGNR|MATERIAL|H-passivated AGNR
n4|N-AGNR|MATERIAL|N-passivated AGNR
co4|CO|ANALYTE|carbon monoxide|target_analyte|-1
co24|CO2|ANALYTE|carbon dioxide''')
    for mat,gas,val,raw in [('h4','CO',-0.446,'−0.446'),('n4','CO',-0.436,'−0.436'),('h4','CO2',-0.426,'−0.426'),('n4','CO2',-0.432,'−0.432')]:
        unitscope='−0.446 and −0.436 eV' if gas=='CO' else '−0.426 and −0.432 eV'
        gasescope='and CO were' if gas=='CO' else 'case of CO2'
        d.r(mat,'HAS_PROPERTY','energy',q=[q('S4',raw,'adsorption_energy',val),q('S4',unitscope,'energy_unit','eV','eV'),q('S4',gasescope,'analyte',gas)])
    d.s('S5','''doping|doped with platinum (Pt)|PROCESS|Pt doping
pt|platinum|MATERIAL|platinum|dopant
ptalias|Pt|MATERIAL|platinum|dopant|-1
h5|H-AGNR|MATERIAL|H-passivated AGNR|material|-1
n5|N-AGNR|MATERIAL|N-passivated AGNR|material|-1
pth|Pt–H-AGNR|MATERIAL|Pt-doped H-AGNR
ptn|Pt–N-AGNR|MATERIAL|Pt-doped N-AGNR''')
    d.r('pth','FABRICATED_BY','doping');d.r('ptn','FABRICATED_BY','doping')
    d.s('S6','''energy6|adsorption energy|PROPERTY|adsorption energy
co6|CO|ANALYTE|carbon monoxide|target_analyte|-1
ptn6|Pt–N-AGNR|MATERIAL|Pt-doped N-AGNR|material|-1
co26|CO2|ANALYTE|carbon dioxide
pth6|Pt–H-AGNR|MATERIAL|Pt-doped H-AGNR
ptn6b|Pt–N-AGNR|MATERIAL|Pt-doped N-AGNR|material|2''')
    for mat,gas in [('ptn6','CO'),('pth6','CO2'),('ptn6b','CO2')]:
        gasescope='CO on Pt–N-AGNR' if gas=='CO' else 'CO2 on both Pt–H-AGNR and Pt–N-AGNR'
        d.r(mat,'HAS_PROPERTY','energy6',mode='COMPARED',q=[q('S6','almost 9 times','relative_energy'),q('S6',gasescope,'analyte',gas),q('S6','non-doped systems','comparison')])
    d.s('S7','''energy7|adsorption energy|PROPERTY|adsorption energy
co7|CO|ANALYTE|carbon monoxide
pth7|Pt–H-AGNR|MATERIAL|Pt-doped H-AGNR''')
    d.r('pth7','HAS_PROPERTY','energy7',mode='COMPARED',q=[q('S7','almost 13 times','relative_energy'),q('S7','CO','analyte')])
    d.s('S8','''energy8|adsorption energy|PROPERTY|adsorption energy
eads|Eads|PROPERTY|adsorption energy
distance|adsorption distance|PROPERTY|adsorption distance
d_alias|D|PROPERTY|adsorption distance|metric_alias|-1
charge|charge transfer|PROPERTY|charge transfer
delta|ΔQ|PROPERTY|charge transfer
dos|density of states|PROPERTY|density of states
dosalias|DOS|PROPERTY|density of states
band|band structure|PROPERTY|band structure
systems|four systems|MATERIAL|four AGNR sensor-material group''')
    for k in ['energy8','distance','charge','dos','band']:d.r('systems','HAS_PROPERTY',k,scope='COMPUTATIONAL_ANALYSIS')
    d.identity('h','n','DIFFERENT','Hydrogen and nitrogen passivation are separate systems.')
    d.identity('h','pth','DIFFERENT','Pt-doped material not SAME as undoped H-AGNR.')
    d.identity('n','ptn','DIFFERENT','Pt-doped material not SAME as undoped N-AGNR.')
    d.data['unresolved'].append(dict(question_id='D042-QENERGY',status='UNRESOLVED',category='NUMERIC_INTERPRETATION',
        reason='Negative initial energies and subsequent increase by almost 9/13 times do not specify signed-value versus magnitude convention; literal ratios retained without converting to new eV values.',
        evidence=[d.sentences[k] for k in ['S4','S6','S7']],
        options={'A':'Читать increase как рост модуля энергии связывания.','B':'Читать increase как арифметический рост signed energy.','C':'Сохранить буквальные factors без нормализации.'},preliminary_recommendation='C'))
    d.finish(['All four negative energies preserve respectively mapping and sign. No 9x/13x absolute energies derived.',
              'Four modeled systems are not experimentally fabricated sensors; no significant changes is a scoped negative.',
              'ATK-VNL is a modeling tool, not a physical synthesis method.'])


def D021():
    d=Record('D021')
    d.s('S1','''composite|graphene-based nanocomposites|MATERIAL|graphene-based nanocomposite class
mechanical|mechanical|PROPERTY|mechanical properties
electrical|electrical|PROPERTY|electrical properties
thermal|thermal|PROPERTY|thermal properties
barrier|barrier properties|PROPERTY|barrier properties''')
    for k in ['mechanical','electrical','thermal','barrier']:d.r('composite','HAS_PROPERTY',k,scope='REVIEW_BACKGROUND')
    d.s('S2','''topdown|simple top-down synthesis|PROCESS|top-down synthesis
go|graphene oxide|MATERIAL|graphene oxide|material|-1
goalias|GO|MATERIAL|graphene oxide|material_alias|-1
rgo|reduced graphene oxide|MATERIAL|reduced graphene oxide
rgoalias|rGO|MATERIAL|reduced graphene oxide
gasbarrier|gas barrier|APPLICATION|gas barrier application
separation|membrane separation|APPLICATION|membrane separation
stimuli|stimuli-response characteristics|PROPERTY|stimuli-response characteristics
composites2|nanocomposites|MATERIAL|graphene-derivative nanocomposite class''')
    for k in ['go','rgo']:
        d.r(k,'FABRICATED_BY','topdown',scope='REVIEW_BACKGROUND')
        for app in ['gasbarrier','separation']:d.r(k,'USED_FOR',app,scope='REVIEW_BACKGROUND')
    d.r('composites2','HAS_PROPERTY','stimuli',scope='REVIEW_BACKGROUND')
    d.s('S3','''synthesis|synthesis techniques|PROCESS|graphene-derivative synthesis
derivatives|graphene derivatives|MATERIAL|GO/rGO derivative class
properties|key material properties|PROPERTY|material properties unspecified
composite3|nanocomposites|MATERIAL|graphene-derivative nanocomposite class''')
    d.r('derivatives','FABRICATED_BY','synthesis',scope='REVIEW_SCOPE')
    d.r('synthesis','AFFECTS','properties',note='Synthesis affects material properties without stating improvement direction; not IMPROVES.')
    d.s('S4','''separation4|separation applications|APPLICATION|separation application
responsive|stimuli-responsive materials|MATERIAL|stimuli-responsive materials
coatings|anti-corrosion coatings|DEVICE|anti-corrosion coating
storage|energy storage|APPLICATION|energy storage''')
    for k in ['separation4','storage']:d.r('composite3','USED_FOR',k,ss=['S3','S4'],scope='REVIEW_SCOPE')
    d.r('coatings','USES_MATERIAL','composite3',ss=['S3','S4'],scope='REVIEW_SCOPE')
    d.s('S5','''production|practical industrial-scale production|PROCESS|industrial-scale polymer nanocomposite production
polymer|graphene-derivative-based polymer nanocomposites|MATERIAL|graphene-derivative polymer nanocomposite''')
    d.r('polymer','FABRICATED_BY','production',mode='HYPOTHETICAL',scope='REVIEW_OUTLOOK',note='Remaining production challenges/outlook, not completed industrial deployment.')
    d.identity('go','rgo','DIFFERENT','GO and rGO are separate graphene derivatives, not aliases.')
    d.finish(['Review field-level claims carry review scope. No fabricated numerical material properties or anti-corrosion efficiency.',
              'GO/rGO/polymer nanocomposites remain distinct; industrial-scale production is an outlook challenge.'])


def D093():
    d=Record('D093')
    d.s('S1','''graphene|Graphene|MATERIAL|graphene
opto|optoelectronics|APPLICATION|optoelectronics
mechanics|mechanics|APPLICATION|mechanics
biochem|bio-chemical sensing|APPLICATION|biochemical sensing
photo|unique photoelectric characteristics|PROPERTY|photoelectric characteristics''')
    d.r('graphene','HAS_PROPERTY','photo',scope='REVIEW_BACKGROUND')
    for k in ['opto','mechanics','biochem']:d.r('graphene','USED_FOR',k,scope='REVIEW_BACKGROUND')
    d.s('S2','''two|two-dimensional nature|MORPHOLOGY|two-dimensional morphology
film|atomically thick film|MATERIAL|graphene
flex|full flexibility|PROPERTY|flexibility
waveguide|optical waveguides|DEVICE|optical waveguide
fiber|fibers|DEVICE|optical fiber
polarizer|polarizers|DEVICE|graphene photonic polarizer
laser|lasers|DEVICE|graphene photonic laser
sensor|sensors|DEVICE|graphene optical sensor''')
    d.rs('''film HAS_MORPHOLOGY two
film HAS_PROPERTY flex''',scope='REVIEW_BACKGROUND')
    d.r('film','INTEGRATED_IN','waveguide',note='Graphene MATERIAL integrated with an optical waveguide; frozen INTEGRATED_IN only permits DEVICE heads.')
    for k in ['polarizer','laser','sensor']:d.r(k,'USES_MATERIAL','film',scope='REVIEW_BACKGROUND')
    d.identity('fiber','waveguide','NARROWER','Fibers are explicitly examples of optical waveguides; not all waveguides are fibers.')
    d.s('S3','''devices|graphene-based optical devices|DEVICE|graphene optical device class
sensor3|sensor|DEVICE|graphene optical sensor
gas|gas sensing|APPLICATION|gas sensing
structures|sensing structures|MORPHOLOGY|sensing structure class''')
    d.r('sensor3','USED_FOR','gas',scope='REVIEW_BACKGROUND')
    d.s('S4','''micro|graphene-based microfiber gas sensors|DEVICE|graphene microfiber gas sensor
principles|sensing principles|MECHANISM|gas sensing principles unspecified
properties|properties|PROPERTY|sensor properties unspecified
fabrication|fabrication|PROCESS|microfiber gas sensor fabrication
interrogation|interrogating|PROCESS|optical interrogation
implementation|implementations|APPLICATION|microfiber sensor implementations''')
    d.rs('''micro HAS_MECHANISM principles
micro HAS_PROPERTY properties
micro FABRICATED_BY fabrication
micro USED_FOR implementation''',scope='REVIEW_SCOPE')
    d.finish(['Atomically thick is preserved literally, without converting to an exact atomic-layer count.',
              'Review topics are generic review scope; no invented LOD/sensitivity or specific sensing mechanism.'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('codes',nargs='*');a=p.parse_args()
    for code in a.codes or ['D018','D050','D029','D042','D021','D093']:globals()[code]()
