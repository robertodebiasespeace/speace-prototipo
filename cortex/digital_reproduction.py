
def crossover_genomes(parent1_dna: Dict, parent2_dna: Dict) -> Dict:
    """
    Combina due DNA digitali per creare un figlio.
    Crossover point casuale nel genome yaml.
    """
    child = {}
    for key in parent1_dna:
        if random.random() < 0.5:
            child[key] = parent1_dna[key]
        else:
            child[key] = parent2_dna.get(key, parent1_dna[key])
    
    # Tasso di mutazione aumentato nella riproduzione
    if random.random() < 0.1:  # 10% mutazione riproduttiva
        child = apply_random_mutation(child)
    
    return child

def natural_selection(population: List[SPEACE_Node], 
                      survival_threshold: float = 0.7) -> List[SPEACE_Node]:
    """Sopravvivono solo i nodi con Φ > threshold"""
    return [node for node in population if node.phi > survival_threshold]