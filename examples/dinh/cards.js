const CARDS = {
  "lote1": [
    {
      "slug": "forearm_stretch",
      "name": "Alongamento de antebraço",
      "place": "Em pé",
      "equip": "",
      "desc": "Estende um braço à frente e puxa a mão com a outra, alongando o antebraço.",
      "also": [],
      "path": "forearm_stretch.json"
    },
    {
      "slug": "shoulder_stretch",
      "name": "Alongamento de ombro",
      "place": "Em pé",
      "equip": "",
      "desc": "Cruza um braço na frente do peito e puxa com o outro, alongando o ombro.",
      "also": [],
      "path": "shoulder_stretch.json"
    },
    {
      "slug": "cobra",
      "name": "Extensão de tronco em prono (Cobra)",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de barriga para baixo, posicione as mãos no chão na altura dos ombros. Empurre o corpo para cima esticando os braços e elevando o peito enquanto olha para o teto. Retorne lentamente à posição inicial apoiando os antebraços no colchonete.",
      "also": [],
      "path": "cobra.json"
    },
    {
      "slug": "squat_reach",
      "name": "Agachamento com alcance",
      "place": "Em pé",
      "equip": "",
      "desc": "Agacha e sobe alcançando os braços para cima.",
      "also": [],
      "path": "squat_reach.json"
    },
    {
      "slug": "reverse_crunches",
      "name": "Abdominal inverso",
      "place": "Deitado",
      "equip": "",
      "desc": "Deitado de costas, eleva o quadril e as pernas em direção ao peito e desce.",
      "also": [],
      "path": "reverse_crunches.json"
    },
    {
      "slug": "step_up_on_chair",
      "name": "Subida na cadeira",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Sobe com um pé na cadeira, sobe o outro e desce.",
      "also": [],
      "path": "step_up_on_chair.json"
    }
  ],
  "lote2": [
    {
      "slug": "walking_hip_opener",
      "name": "Abertura de quadril caminhando",
      "place": "Em pé",
      "equip": "",
      "desc": "Passos largos com abertura de quadril, tronco ereto.",
      "also": [],
      "path": "walking_hip_opener.json"
    },
    {
      "slug": "lunge",
      "name": "Afundo",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, dê um passo largo à frente e flexione os joelhos, descendo o quadril em direção ao chão até que a perna de trás quase toque o solo. Mantenha o tronco ereto e o olhar para frente durante a descida. Empurre o chão com a perna da frente para retornar à posição inicial com os pés juntos.",
      "also": [],
      "path": "lunge.json"
    },
    {
      "slug": "military_push_ups",
      "name": "Flexão de braços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Comece em posição de prancha, com as mãos apoiadas no chão na largura dos ombros e o corpo bem alinhado. Dobre os cotovelos para descer o tronco em direção ao solo, mantendo a coluna reta e o abdômen contraído. Empurre o chão com força para retornar à posição inicial com os braços estendidos.",
      "also": [],
      "path": "military_push_ups.json"
    },
    {
      "slug": "wide_arm_push_up",
      "name": "Flexão com braços abertos",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Flexão com as mãos mais afastadas que os ombros.",
      "also": [],
      "path": "wide_arm_push_up.json"
    },
    {
      "slug": "staggered_push_ups",
      "name": "Flexão escalonada",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Flexão com uma mão mais à frente que a outra.",
      "also": [],
      "path": "staggered_push_ups.json"
    },
    {
      "slug": "t_plank",
      "name": "Prancha em T",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Da prancha, gira o tronco e abre o braço para o teto.",
      "also": [],
      "path": "t_plank.json"
    },
    {
      "slug": "press_up_toe_tap",
      "name": "Prancha com toque do pé",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Em prancha, toca o pé para o lado e volta.",
      "also": [],
      "path": "press_up_toe_tap.json"
    },
    {
      "slug": "punches",
      "name": "Socos frontais alternados",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com os joelhos levemente flexionados e punhos cerrados próximos ao rosto. Estenda um braço à frente em um movimento de soco, girando levemente o tronco e o quadril, e retorne à posição inicial. Repita o movimento alternando os braços de forma rítmica.",
      "also": [],
      "path": "punches.json"
    },
    {
      "slug": "frog_press",
      "name": "Frog press",
      "place": "Deitado",
      "equip": "",
      "desc": "Deitado, joelhos abertos, estende e flexiona as pernas.",
      "also": [],
      "path": "frog_press.json"
    },
    {
      "slug": "seated_abs_circles",
      "name": "Círculos abdominais sentado",
      "place": "Sentado",
      "equip": "",
      "desc": "Sentado, pernas elevadas, desenha círculos com o tronco.",
      "also": [],
      "path": "seated_abs_circles.json"
    },
    {
      "slug": "squat_kicks",
      "name": "Agachamento com chute",
      "place": "Em pé",
      "equip": "",
      "desc": "Agacha e, na subida, chuta uma perna à frente.",
      "also": [],
      "path": "squat_kicks.json"
    },
    {
      "slug": "jumping_squats",
      "name": "Agachamento com salto",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé com as mãos na cintura, realize um agachamento projetando o quadril para trás. Salte verticalmente de forma explosiva e, ao aterrissar, dobre os joelhos suavemente para retornar à posição de agachamento. Repita o movimento de forma contínua.",
      "also": [],
      "path": "jumping_squats.json"
    },
    {
      "slug": "jumping_jack",
      "name": "Polichinelo",
      "place": "Em pé",
      "equip": "",
      "desc": "Comece em pé com os pés juntos e braços ao lado do corpo. Dê um pequeno salto afastando as pernas lateralmente enquanto eleva os braços acima da cabeça. Salte novamente para unir os pés e abaixar os braços, retornando à posição inicial.",
      "also": [],
      "path": "jumping_jack.json"
    },
    {
      "slug": "split_jump",
      "name": "Split jump",
      "place": "Em pé",
      "equip": "",
      "desc": "Salta alternando a perna da frente no ar.",
      "also": [],
      "path": "split_jump.json"
    },
    {
      "slug": "box_jump",
      "name": "Salto na caixa",
      "place": "Em pé",
      "equip": "caixa",
      "desc": "Salta sobre a caixa e desce com controle.",
      "also": [],
      "path": "box_jump.json"
    },
    {
      "slug": "burpee_and_jump",
      "name": "Burpee",
      "place": "Em pé",
      "equip": "",
      "desc": "Comece em pé, agache e apoie as mãos no chão à frente. Salte com os pés para trás para ficar em posição de prancha, realize uma flexão de braços e salte novamente trazendo os pés para perto das mãos. Finalize com um salto vertical explosivo, estendendo os braços para o alto.",
      "also": [],
      "path": "burpee_and_jump.json"
    },
    {
      "slug": "inchworm",
      "name": "Inchworm",
      "place": "Em pé",
      "equip": "",
      "desc": "Com as mãos no chão, anda até a prancha e volta.",
      "also": [],
      "path": "inchworm.json"
    },
    {
      "slug": "clean_and_press",
      "name": "Clean and press com barra",
      "place": "Em pé",
      "equip": "barra",
      "desc": "Puxa a barra até os ombros e empurra acima da cabeça.",
      "also": [],
      "path": "clean_and_press.json"
    }
  ],
  "lote3": [
    {
      "slug": "sit_to_stand_exercise",
      "path": "puppet/sit_to_stand_exercise.json",
      "name": "Sentar e levantar da cadeira com braços cruzados",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sente-se em uma cadeira com os pés apoiados no chão e cruze os braços sobre o peito, tocando os ombros opostos. Levante-se totalmente mantendo o tronco ereto e sem descruzar os braços. Retorne à posição sentada de forma lenta e controlada.",
      "also": []
    },
    {
      "slug": "seated_knee_extension",
      "path": "puppet/seated_knee_extension.json",
      "name": "Flexão e extensão de joelho sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com as costas retas e os pés suspensos, dobre o joelho levando o calcanhar para trás o máximo que puder. Em seguida, estenda a perna totalmente para a frente até que ela fique reta. Retorne o pé para a posição inicial e repita o movimento de forma controlada.",
      "also": []
    },
    {
      "slug": "mini_squat",
      "path": "puppet/mini_squat.json",
      "name": "Mini agachamento com toque em superfície elevada",
      "place": "Em pé",
      "equip": "cadeira · travesseiro",
      "desc": "Em pé, de costas para uma cadeira com almofadas, mantenha os pés afastados na largura dos ombros. Flexione levemente os joelhos e quadris enquanto leva os braços à frente, até tocar levemente as almofadas com o glúteo. Retorne à posição inicial estendendo as pernas e baixando os braços de forma controlada.",
      "also": []
    },
    {
      "slug": "standing_hip_flexion",
      "path": "puppet/standing_hip_flexion.json",
      "name": "Marcha estacionária com apoio",
      "place": "Em pé",
      "equip": "apoio",
      "desc": "Em pé, posicione-se de frente para uma superfície estável, apoiando levemente as pontas dos dedos para equilíbrio. Eleve um joelho em direção ao peito de forma controlada e retorne o pé ao chão. Repita o movimento alternando as pernas, mantendo o tronco ereto durante todo o exercício.",
      "also": []
    },
    {
      "slug": "standing_hip_extension",
      "path": "puppet/standing_hip_extension.json",
      "name": "Extensão de quadril em pé com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, segure no encosto de uma cadeira estável para manter o equilíbrio. Leve uma das pernas para trás mantendo o joelho esticado e o tronco ereto, sem inclinar o corpo para frente. Retorne a perna devagar à posição inicial e repita o movimento.",
      "also": []
    },
    {
      "slug": "standing_knee_flexion",
      "path": "puppet/standing_knee_flexion.json",
      "name": "Flexão de joelho em pé com caneleira",
      "place": "Em pé",
      "equip": "cadeira · caneleira",
      "desc": "Em pé, segure no encosto de uma cadeira para manter o equilíbrio. Dobre o joelho de uma das pernas levando o calcanhar em direção ao bumbum, sem deixar a coxa ir para frente. Retorne o pé ao chão devagar e repita o movimento.",
      "also": []
    },
    {
      "slug": "standing_marching",
      "path": "puppet/standing_marching.json",
      "name": "Marcha estacionária com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, posicione-se ao lado de uma cadeira estável para segurança. Eleve um joelho de cada vez em direção ao peito, alternando as pernas como se estivesse marchando sem sair do lugar. Mantenha o corpo ereto e o olhar para frente durante todo o movimento.",
      "also": []
    },
    {
      "slug": "indoor_walking",
      "path": "puppet/indoor_walking.json",
      "name": "Caminhada normal",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com a coluna ereta e os braços relaxados ao lado do corpo. Caminhe para frente de maneira natural, alternando os passos com um ritmo constante e equilibrado. Mantenha o olhar fixo à frente e permita que os braços balancem levemente durante o movimento.",
      "also": []
    },
    {
      "slug": "feet_together_stance",
      "path": "puppet/feet_together_stance.json",
      "name": "Equilíbrio estático com pés juntos",
      "place": "Em pé",
      "equip": "",
      "desc": "Fique em pé com os pés unidos, tocando um ao outro. Mantenha o corpo alinhado e o olhar fixo em um ponto à frente. Sustente essa posição tentando minimizar as oscilações do corpo.",
      "also": [
        "Equilíbrio em pé com pés juntos"
      ]
    },
    {
      "slug": "semi_tandem_stance",
      "path": "puppet/semi_tandem_stance.json",
      "name": "Equilíbrio em posição semi-tandem",
      "place": "Em pé",
      "equip": "",
      "desc": "Fique em pé com os braços relaxados ao lado do corpo. Posicione um pé um pouco à frente do outro, mantendo-os próximos, e sustente o equilíbrio por alguns segundos. Repita o exercício trocando a posição dos pés.",
      "also": []
    },
    {
      "slug": "ankle_pumps",
      "path": "puppet/ankle_pumps.json",
      "name": "Dorsiflexão de tornozelo sentado (pernas esticadas)",
      "place": "Sentado",
      "equip": "cama",
      "desc": "Sentado na cama com as pernas esticadas e os pés para fora da borda, puxe as pontas dos pés para cima em direção às canelas. Mantenha os joelhos bem esticados e as mãos apoiadas ao lado do corpo para suporte. Retorne os pés lentamente para a posição inicial e repita.",
      "also": []
    },
    {
      "name": "Bombeamento de tornozelos deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, com as pernas esticadas, puxe as pontas dos pés em direção ao corpo e depois aponte-as para longe. O catálogo publicado não descreve este gesto em supino.",
      "also": [],
      "slug": "supine_ankle_pumps",
      "path": "puppet/supine_ankle_pumps.json"
    },
    {
      "slug": "heel_slides",
      "path": "puppet/heel_slides.json",
      "name": "Deslizamento de calcanhar em supino",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas com os joelhos dobrados e pés no chão, mantenha o abdômen contraído. Deslize lentamente um calcanhar pelo chão até esticar a perna completamente. Retorne puxando o pé de volta à posição inicial, mantendo o quadril parado e a coluna apoiada.",
      "also": [
        "Flexão de pernas alternada em decúbito dorsal",
        "Deslizamento de calcanhar com ativação abdominal"
      ]
    },
    {
      "slug": "double_heel_slides",
      "path": "puppet/double_heel_slides.json",
      "name": "Deslizamento de calcanhares duplo em decúbito dorsal",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitada de costas com os joelhos dobrados e pés apoiados, coloque as mãos sobre os ossos do quadril para monitorar a estabilidade. Escorregue os dois calcanhares para frente ao mesmo tempo até esticar completamente as pernas, mantendo a coluna e a bacia imóveis. Puxe os pés de volta para a posição inicial de forma lenta e controlada.",
      "also": []
    },
    {
      "slug": "bridge",
      "path": "puppet/bridge.json",
      "name": "Ponte",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com os joelhos dobrados e os pés apoiados no chão. Eleve o quadril em direção ao teto até que o corpo forme uma linha reta dos ombros aos joelhos. Retorne lentamente à posição inicial, encostando o quadril no colchonete.",
      "also": [
        "Ponte pélvica articulada"
      ]
    },
    {
      "slug": "single_leg_bridge",
      "path": "puppet/single_leg_bridge.json",
      "name": "Ponte unilateral com perna estendida",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com um joelho dobrado e o pé apoiado, enquanto a outra perna permanece esticada no chão. Eleve o quadril em direção ao teto, mantendo a perna esticada alinhada ao corpo, e sustente a posição por um momento. Retorne o quadril lentamente ao colchonete e repita o movimento.",
      "also": [
        "Ponte unilateral com elevação de perna estendida",
        "Ponte unilateral"
      ]
    },
    {
      "slug": "straight_leg_raise",
      "path": "puppet/straight_leg_raise.json",
      "name": "Elevação da perna estendida (SLR) em decúbito dorsal",
      "place": "Deitado",
      "equip": "cama",
      "desc": "Deitado de costas, dobre um joelho apoiando o pé na cama e mantenha a outra perna esticada. Eleve a perna esticada até a altura do outro joelho, mantendo o joelho bem reto. Retorne lentamente à posição inicial.",
      "also": [
        "Elevação de perna estendida (SLR)",
        "Elevação de perna esticada (SLR)",
        "Elevação de perna estendida (supino)"
      ]
    },
    {
      "slug": "supine_pelvic_tilt",
      "path": "puppet/supine_pelvic_tilt.json",
      "name": "Báscula de pelve em decúbito dorsal",
      "place": "Deitado",
      "equip": "colchonete · cama",
      "desc": "Deitado de costas com os joelhos dobrados e pés apoiados, cruze os braços sobre o peito. Contraia o abdômen para achatar a coluna lombar contra a superfície, elevando levemente o cóccix. Mantenha a contração por um momento e retorne à posição inicial relaxando a pelve.",
      "also": []
    },
    {
      "slug": "abdominal_crunches",
      "path": "puppet/abdominal_crunches.json",
      "name": "Abdominal supra com joelhos flexionados",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com os joelhos dobrados e os pés apoiados no chão. Eleve a cabeça e a parte superior das costas, mantendo os braços estendidos e paralelos ao chão, contraindo o abdômen. Retorne suavemente à posição inicial e repita o movimento.",
      "also": []
    },
    {
      "slug": "cat_camel",
      "path": "puppet/cat_camel.json",
      "name": "Gato e Camelo",
      "place": "Quatro apoios",
      "equip": "colchonete",
      "desc": "Fique em quatro apoios, com as mãos alinhadas aos ombros e joelhos aos quadris. Arredonde as costas para cima, levando o queixo em direção ao peito e contraindo o abdômen. Depois, inverta o movimento arqueando as costas para baixo e olhando suavemente para frente.",
      "also": []
    },
    {
      "slug": "prone_hip_extension",
      "path": "puppet/prone_hip_extension.json",
      "name": "Extensão de quadril em quatro apoios (Coice)",
      "place": "Quatro apoios",
      "equip": "colchonete",
      "desc": "Comece na posição de quatro apoios, com as mãos alinhadas aos ombros e joelhos sob o quadril. Eleve uma das pernas mantendo o joelho dobrado em 90 graus, levando a sola do pé em direção ao teto. Retorne o joelho devagar em direção ao chão e repita o movimento sem girar o tronco.",
      "also": []
    },
    {
      "slug": "lying_to_sitting",
      "path": "puppet/lying_to_sitting.json",
      "name": "Transição de deitado para sentado na beira da cama",
      "place": "Deitado",
      "equip": "cama",
      "desc": "Deitado de costas, dobre os joelhos um de cada vez e gire o corpo para o lado. Leve as pernas para fora da cama e use o peso dos pés descendo para ajudar a empurrar o tronco com os braços. Finalize sentado firmemente na borda da cama com os pés pendentes.",
      "also": []
    }
  ],
  "lote4": [
    {
      "slug": "step_up",
      "path": "puppet/step_up.json",
      "name": "Subida no degrau",
      "place": "Em pé",
      "equip": "degrau",
      "desc": "Fique em pé de frente para um degrau firme e coloque um pé sobre ele. Suba no degrau fazendo força apenas com a perna de cima, mantendo o tronco ereto. Desça de forma controlada até tocar o chão novamente.",
      "also": [
        "Subida no degrau (Step-up)",
        "Subida e descida no degrau",
        "Subida no degrau com equilíbrio"
      ]
    },
    {
      "slug": "wall_push_up",
      "path": "puppet/wall_push_up.json",
      "name": "Flexão de braços na parede",
      "place": "Em pé",
      "equip": "parede",
      "desc": "Em pé, apoie as mãos na parede na altura do peito e afaste os pés para trás, mantendo o corpo inclinado e reto. Dobre os cotovelos aproximando o peito da parede de forma controlada. Empurre o corpo de volta até esticar os braços totalmente, retornando à posição inicial.",
      "also": []
    },
    {
      "slug": "wall_ball_squat",
      "path": "puppet/wall_ball_squat.json",
      "name": "Agachamento na parede com bola suíça e braços à frente",
      "place": "Em pé",
      "equip": "bola · parede",
      "desc": "Em pé, posicione a bola entre a sua lombar e a parede, com os pés um pouco à frente e braços esticados para frente. Agache lentamente deslizando a bola pela parede até onde for confortável, mantendo os braços estendidos. Retorne à posição inicial esticando os joelhos.",
      "also": [
        "Agachamento na parede com bola suíça",
        "Agachamento na parede com bola"
      ]
    },
    {
      "slug": "standing_heel_raise",
      "path": "puppet/standing_heel_raise.json",
      "name": "Elevação de calcanhares em pé com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, apoie as mãos no encosto de uma cadeira estável para manter o equilíbrio. Eleve os calcanhares ficando na ponta dos pés e retorne devagar ao chão. Mantenha os joelhos esticados durante todo o exercício.",
      "also": []
    },
    {
      "slug": "variable_speed_walking",
      "path": "puppet/variable_speed_walking.json",
      "name": "Caminhada com aceleração progressiva",
      "place": "Em pé",
      "equip": "",
      "desc": "Comece caminhando em um ritmo lento e confortável. Aumente gradualmente a velocidade dos passos a cada metro percorrido, até atingir uma caminhada rápida e vigorosa. Mantenha o tronco ereto e os braços balançando naturalmente ao lado do corpo.",
      "also": []
    },
    {
      "slug": "single_leg_stance",
      "path": "puppet/single_leg_stance.json",
      "name": "Equilíbrio unipodal com olhos abertos e apoio próximo",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, posicione-se ao lado de uma cadeira estável para segurança. Retire um pé do chão, dobrando levemente o joelho, e mantenha o equilíbrio apenas na outra perna pelo tempo recomendado. Retorne o pé ao chão de forma controlada.",
      "also": [
        "Equilíbrio unipodal com apoio de cadeira",
        "Equilíbrio unipodal ao lado da cadeira",
        "Equilíbrio unipodal com apoio"
      ]
    },
    {
      "slug": "standing_quad_stretch",
      "path": "puppet/standing_quad_stretch.json",
      "name": "Alongamento de quadríceps em pé com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, apoie as mãos no encosto de uma cadeira para manter o equilíbrio. Dobre um joelho para trás e segure o tornozelo com a mão do mesmo lado, puxando o calcanhar em direção ao glúteo. Mantenha a posição por alguns segundos com o corpo ereto e depois retorne o pé ao chão, alternando as pernas.",
      "also": []
    },
    {
      "slug": "standing_hip_abduction",
      "path": "puppet/standing_hip_abduction.json",
      "name": "Abdução de quadril em pé com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, com uma das mãos apoiada em uma cadeira para equilíbrio, mantenha o corpo ereto. Afaste a perna lateralmente sem inclinar o tronco, mantendo o joelho esticado. Retorne a perna devagar até a posição inicial.",
      "also": []
    },
    {
      "slug": "lateral_weight_shift",
      "path": "puppet/lateral_weight_shift.json",
      "name": "Transferência de peso lateral em pé",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, com as mãos apoiadas em uma superfície firme à frente, mantenha os pés afastados. Desloque o peso do corpo suavemente para um dos lados, mantendo o tronco reto e os joelhos estendidos. Retorne à posição central e repita conforme a orientação.",
      "also": []
    },
    {
      "slug": "ankle_circles",
      "path": "puppet/ankle_circles.json",
      "name": "Circundução de tornozelo em pé com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé ao lado de uma cadeira, apoie uma das mãos no encosto para manter o equilíbrio. Retire um dos pés do chão e realize movimentos circulares lentos e amplos com o tornozelo, como se estivesse desenhando um círculo com a ponta do pé. Após completar as repetições, retorne o pé ao chão e repita com o outro lado.",
      "also": []
    },
    {
      "slug": "shoulder_shrugs",
      "path": "puppet/shoulder_shrugs.json",
      "name": "Encolhimento de ombros com halteres",
      "place": "Em pé",
      "equip": "halter",
      "desc": "Em pé, segure um halter em cada mão com os braços esticados ao lado do corpo. Eleve os ombros em direção às orelhas o máximo que puder sem dobrar os cotovelos. Retorne lentamente à posição inicial, relaxando os ombros.",
      "also": []
    },
    {
      "slug": "band_pull_apart",
      "path": "puppet/band_pull_apart.json",
      "name": "Crucifixo inverso com faixa elástica em pé",
      "place": "Em pé",
      "equip": "faixa",
      "desc": "Em pé, segure a faixa elástica com as duas mãos à frente do peito e os braços esticados. Afaste as mãos para os lados até que os braços fiquem alinhados com os ombros, formando um 'T' com o corpo. Retorne lentamente à posição inicial mantendo o controle do movimento.",
      "also": []
    },
    {
      "slug": "band_shoulder_external_rotation",
      "path": "puppet/band_shoulder_external_rotation.json",
      "name": "Rotação externa de ombro com elástico (fase excêntrica)",
      "place": "Em pé",
      "equip": "faixa",
      "desc": "Em pé, segure a ponta de um elástico preso lateralmente com o cotovelo dobrado em 90 graus. Use a outra mão para puxar o antebraço para fora, girando o ombro. Solte a mão de apoio e retorne o braço lentamente para a posição inicial, resistindo à força do elástico.",
      "also": [
        "Rotação externa de ombro com elástico"
      ]
    },
    {
      "slug": "seated_knee_extension_ankle_weight",
      "path": "puppet/seated_knee_extension_ankle_weight.json",
      "name": "Extensão de joelho sentado com caneleira",
      "place": "Sentado",
      "equip": "cadeira · caneleira",
      "desc": "Sentado em uma cadeira com as costas apoiadas, estenda o joelho levando o pé para frente até a perna ficar reta. Mantenha a posição por um breve momento e retorne o pé ao chão de forma lenta e controlada. Mantenha o tronco estável durante todo o exercício.",
      "also": [
        "Extensão de joelho sentada com carga (45 graus)"
      ]
    },
    {
      "slug": "seated_shoulder_flexion",
      "path": "puppet/seated_shoulder_flexion.json",
      "name": "Flexão de ombros sentada com respiração",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com os braços relaxados ao lado do corpo. Inspire profundamente enquanto eleva os braços esticados para frente e para cima. Expire lentamente enquanto retorna os braços para a posição inicial.",
      "also": []
    },
    {
      "slug": "seated_shoulder_abduction",
      "path": "puppet/seated_shoulder_abduction.json",
      "name": "Abdução de ombro sentado (até 180°)",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com a coluna ereta, mantenha o braço esticado ao lado do corpo. Eleve o braço lateralmente em um arco amplo até que ele aponte para o teto, mantendo o cotovelo sempre reto. Retorne o braço devagar para a posição inicial ao lado da coxa.",
      "also": []
    },
    {
      "slug": "seated_overhead_press",
      "path": "puppet/seated_overhead_press.json",
      "name": "Desenvolvimento de ombro unilateral sentado com halter",
      "place": "Sentado",
      "equip": "cadeira · halter",
      "desc": "Sentado em uma cadeira com a coluna ereta, segure o halter na altura do ombro com o cotovelo dobrado. Eleve o braço em direção ao teto até esticá-lo completamente. Retorne o peso de forma controlada para a posição inicial próxima ao ombro.",
      "also": []
    },
    {
      "slug": "elbow_flexion_dumbbell",
      "path": "puppet/elbow_flexion_dumbbell.json",
      "name": "Rosca martelo sentado com halter",
      "place": "Sentado",
      "equip": "cadeira · halter",
      "desc": "Sentado, segure um halter com a palma da mão voltada para o corpo e o braço estendido ao lado do tronco. Dobre o cotovelo levando o peso em direção ao ombro, mantendo o braço próximo ao corpo. Retorne lentamente à posição inicial.",
      "also": []
    },
    {
      "slug": "arm_circles",
      "path": "puppet/arm_circles.json",
      "name": "Circundução de ombros sentado (alternado)",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com as costas eretas, mantenha os braços relaxados ao lado do corpo. Com o cotovelo esticado, realize um círculo amplo com um braço, levando-o para frente, para cima e para trás, alternando com o outro braço. Após completar a sequência, realize o movimento no sentido inverso, circulando o braço para trás e para baixo.",
      "also": []
    },
    {
      "slug": "seated_trunk_rotation",
      "path": "puppet/seated_trunk_rotation.json",
      "name": "Rotação de tronco sentado com faixa elástica lateral",
      "place": "Sentado",
      "equip": "cadeira · faixa",
      "desc": "Sentado em uma cadeira, segure a ponta de uma faixa elástica presa lateralmente com as duas mãos à frente do corpo. Gire o tronco lentamente para o lado oposto ao elástico, mantendo os braços esticados. Retorne à posição inicial de forma controlada.",
      "also": []
    },
    {
      "slug": "seated_band_row",
      "path": "puppet/seated_band_row.json",
      "name": "Remada baixa sentada com faixa elástica",
      "place": "Sentado",
      "equip": "cadeira · faixa",
      "desc": "Sentado em uma cadeira com a coluna ereta, segure as pontas de uma faixa elástica presa à sua frente. Puxe a faixa em direção à cintura, levando os cotovelos para trás e aproximando as escápulas (as 'asas' das costas). Retorne lentamente à posição inicial com os braços estendidos à frente.",
      "also": []
    },
    {
      "name": "Abdução de quadril sentado com faixa",
      "place": "Sentado",
      "equip": "cadeira · faixa",
      "desc": "Sentado, com a faixa em volta das coxas logo acima dos joelhos, afaste os joelhos e volte devagar. Não há um exercício publicado no catálogo com este gesto.",
      "also": [],
      "slug": "seated_band_hip_abduction",
      "path": "puppet/seated_band_hip_abduction.json"
    },
    {
      "slug": "adductor_ball_squeeze",
      "path": "puppet/adductor_ball_squeeze.json",
      "name": "Isometria de adutores sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com os pés apoiados no chão, coloque a mão na parte interna do joelho oposto. Empurre o joelho para dentro contra a resistência da mão, mantendo a perna parada sem tirar o pé do lugar. Sustente a força pelo tempo recomendado e relaxe.",
      "also": []
    },
    {
      "slug": "long_sit_quad_set",
      "path": "puppet/long_sit_quad_set.json",
      "name": "Isometria de quadríceps sentado",
      "place": "Sentado",
      "equip": "cama",
      "desc": "Sentada com uma perna esticada e a outra dobrada, puxe a ponta do pé para cima. Contraia o músculo da coxa, empurrando a parte de trás do joelho contra a maca. Mantenha a contração por alguns segundos e depois relaxe.",
      "also": [
        "Extensão terminal de joelho sentado"
      ]
    },
    {
      "slug": "bed_rolling",
      "path": "puppet/bed_rolling.json",
      "name": "Rolo de estabilização de tronco",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com um joelho dobrado e o cotovelo do braço oposto também flexionado. Gire o corpo lateralmente em direção ao lado do joelho dobrado, usando a força do abdômen sem empurrar o chão com os braços. Retorne lentamente à posição inicial e repita trocando o lado do joelho e do braço.",
      "also": []
    },
    {
      "slug": "short_arc_quad",
      "path": "puppet/short_arc_quad.json",
      "name": "Extensão terminal de joelho com rolo",
      "place": "Deitado",
      "equip": "rolo · cama",
      "desc": "Deite-se de costas com um rolo sob os joelhos e os calcanhares apoiados na cama. Estique uma das pernas contraindo o músculo da coxa até que o pé se eleve e o joelho fique reto. Retorne o calcanhar lentamente à posição inicial e repita o movimento.",
      "also": [
        "Fortalecimento de vasto medial com rolo",
        "Extensão terminal de joelho sentado com rolo"
      ]
    },
    {
      "slug": "single_knee_to_chest",
      "path": "puppet/single_knee_to_chest.json",
      "name": "Flexão de quadril alternada com pernas na cadeira",
      "place": "Deitado",
      "equip": "colchonete · cadeira",
      "desc": "Deite-se de costas com as panturrilhas apoiadas em uma cadeira e as mãos posicionadas sob a região lombar. Traga um joelho em direção ao peito de forma lenta e controlada, mantendo a outra perna relaxada no apoio. Retorne o pé para a cadeira e repita o movimento com a perna oposta.",
      "also": []
    },
    {
      "slug": "elbow_flexion",
      "path": "puppet/elbow_flexion.json",
      "name": "Flexão de cotovelo deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com os braços esticados ao lado do corpo e as palmas das mãos voltadas para cima. Dobre os cotovelos trazendo as mãos em direção aos ombros. Estique os braços novamente para retornar à posição inicial.",
      "also": []
    },
    {
      "slug": "supine_hip_abduction",
      "path": "puppet/supine_hip_abduction.json",
      "name": "Abdução de quadril em decúbito dorsal",
      "place": "Deitado",
      "equip": "cama",
      "desc": "Deitado de costas com as pernas esticadas, afaste uma das pernas para o lado mantendo o joelho reto e a ponta do pé para cima. Retorne a perna lentamente para a posição inicial junto à outra. Mantenha o tronco e a outra perna parados durante todo o movimento.",
      "also": []
    },
    {
      "slug": "scapular_retraction",
      "path": "puppet/scapular_retraction.json",
      "name": "Retração escapular em prono com apoio",
      "place": "De bruços",
      "equip": "colchonete · travesseiro",
      "desc": "Deite-se de barriga para baixo com um travesseiro sob o tronco e a testa apoiada no colchonete. Com os braços esticados ao lado do corpo, levante as mãos do chão unindo as escápulas no centro das costas. Retorne os braços ao chão de forma controlada.",
      "also": []
    },
    {
      "slug": "prone_press_up_on_elbows",
      "path": "puppet/prone_press_up_on_elbows.json",
      "name": "Mobilização escapular em prono sobre cotovelos",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deite-se de barriga para baixo apoiado nos cotovelos e antebraços. Deixe o tronco descer lentamente aproximando as escápulas uma da outra sem dobrar os braços. Empurre o chão com os cotovelos para afastar as escápulas e elevar o tronco, retornando à posição inicial.",
      "also": []
    }
  ],
  "lote5": [
    {
      "slug": "chair_march",
      "path": "puppet/chair_march.json",
      "name": "Flexão de quadril sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com os pés no chão, eleve um dos joelhos em direção ao teto mantendo a coluna ereta. Retorne o pé à posição inicial de forma lenta e controlada.",
      "also": []
    },
    {
      "slug": "chair_cat_cow",
      "path": "puppet/chair_cat_cow.json",
      "name": "Mobilização pélvica sentada",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com as mãos nos joelhos, comece arredondando as costas e deslizando o quadril para trás. Em seguida, empine o bumbum, estufando o peito e alinhando a coluna de forma ereta. Retorne à posição inicial e repita o movimento de forma controlada.",
      "also": []
    },
    {
      "slug": "chair_twist",
      "path": "puppet/chair_twist.json",
      "name": "Rotação de tronco sentado com braços cruzados",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentada em uma cadeira com a coluna ereta, cruze os braços sobre o peito tocando os ombros. Gire o tronco lentamente para um lado o máximo que conseguir, mantendo o quadril fixo no assento, e depois gire para o outro lado. Retorne à posição inicial de forma controlada.",
      "also": []
    },
    {
      "slug": "seated_front_raise",
      "path": "puppet/seated_front_raise.json",
      "name": "Elevação frontal de ombros alternada sentado com halteres",
      "place": "Sentado",
      "equip": "cadeira · halter",
      "desc": "Sentado em uma cadeira com a coluna ereta, segure um halter em cada mão com os braços ao lado do corpo. Eleve um braço à frente até a altura do ombro, mantendo o cotovelo quase esticado, e retorne à posição inicial. Repita o movimento alternando os braços de forma controlada.",
      "also": []
    },
    {
      "slug": "dead_bug",
      "path": "puppet/dead_bug.json",
      "name": "Dead Bug (Inseto Morto)",
      "place": "Deitado",
      "equip": "colchonete · cama",
      "desc": "Deitado de costas, mantenha as pernas dobradas no ar e os braços esticados para o teto. Desça um braço para trás da cabeça enquanto estica a perna do lado oposto em direção ao chão, sem encostar no apoio. Retorne devagar à posição inicial e repita o movimento trocando os lados.",
      "also": [
        "Dead Bug (Coordenação Braços e Pernas)"
      ]
    },
    {
      "slug": "split_squat",
      "path": "puppet/split_squat.json",
      "name": "Afundo parcial estático",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, dê um passo largo à frente e mantenha as mãos na cintura para equilíbrio. Flexione os joelhos descendo o corpo em linha reta até uma profundidade média, sem tocar o joelho de trás no chão. Estenda as pernas para retornar à posição inicial, mantendo os pés afastados durante as repetições.",
      "also": [
        "Agachamento unilateral (Split Squat)"
      ]
    },
    {
      "slug": "mini_squat_supported",
      "path": "puppet/mini_squat_supported.json",
      "name": "Agachamento parcial com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, posicione-se de frente para uma cadeira e apoie as mãos no encosto para equilíbrio. Flexione levemente os joelhos e o quadril como se fosse sentar, mantendo as costas retas e os calcanhares no chão. Retorne devagar à posição inicial estendendo as pernas.",
      "also": []
    },
    {
      "slug": "squat_dumbbells",
      "path": "puppet/squat_dumbbells.json",
      "name": "Agachamento profundo com halteres",
      "place": "Em pé",
      "equip": "halter",
      "desc": "Em pé, com os pés afastados na largura dos ombros, segure um halter em cada mão ao lado do corpo. Agache dobrando os joelhos e o quadril o máximo que conseguir, mantendo os calcanhares no chão. Retorne à posição inicial esticando as pernas de forma controlada.",
      "also": [
        "Agachamento com halteres"
      ]
    },
    {
      "slug": "wall_squat",
      "path": "puppet/wall_squat.json",
      "name": "Agachamento na parede",
      "place": "Em pé",
      "equip": "parede",
      "desc": "Fique de pé com as costas apoiadas em uma parede e os pés posicionados um pouco à frente. Deslize o tronco para baixo até que as coxas fiquem paralelas ao chão e os joelhos formem um ângulo de 90 graus. Retorne à posição inicial deslizando as costas para cima pela parede.",
      "also": [
        "Agachamento isométrico na parede"
      ]
    },
    {
      "slug": "march_arms_forward",
      "path": "puppet/march_arms_forward.json",
      "name": "Marcha estacionária com braços elevados a 90 graus",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, estenda os braços para frente na altura dos ombros e mantenha-os fixos. Comece a marchar no lugar, elevando os joelhos alternadamente enquanto mantém o tronco ereto. Retorne o pé ao chão e repita com a outra perna, mantendo os braços sempre esticados.",
      "also": []
    },
    {
      "slug": "ladder_step",
      "path": "puppet/ladder_step.json",
      "name": "Caminhada na escada de agilidade (passo a passo)",
      "place": "Em pé",
      "equip": "escada",
      "desc": "Em pé de frente para a escada no chão, dê um passo com um pé dentro do primeiro quadrado e traga o outro pé para o mesmo espaço. Repita o processo em cada quadrado até chegar ao final da escada. Vire-se e retorne da mesma forma, tentando alternar o pé que inicia o passo.",
      "also": [
        "Caminhada na escada de agilidade (dois pés por quadrado)"
      ]
    },
    {
      "slug": "band_chest_press",
      "path": "puppet/band_chest_press.json",
      "name": "Supino em pé com elástico",
      "place": "Em pé",
      "equip": "faixa",
      "desc": "Em pé com um pé à frente do outro para equilíbrio, segure as pontas da faixa elástica que está presa atrás de você na altura dos ombros. Empurre as mãos para frente até esticar os braços, mantendo o peito aberto e o corpo reto. Retorne lentamente dobrando os cotovelos até as mãos chegarem perto do peito.",
      "also": []
    },
    {
      "slug": "standing_shoulder_extension",
      "path": "puppet/standing_shoulder_extension.json",
      "name": "Extensão de ombro em pé",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com a postura ereta e braços relaxados, leve um dos braços para trás mantendo o cotovelo esticado. Segure a posição por alguns segundos sem deixar o corpo inclinar para frente. Retorne lentamente à posição inicial.",
      "also": []
    },
    {
      "slug": "stick_shoulder_flexion",
      "path": "puppet/stick_shoulder_flexion.json",
      "name": "Flexão de ombro com bastão",
      "place": "Em pé",
      "equip": "bastão",
      "desc": "Em pé, segure um bastão com as duas mãos à frente das coxas. Eleve os braços mantendo-os esticados até que o bastão esteja acima da cabeça. Retorne controladamente à posição inicial.",
      "also": []
    },
    {
      "slug": "wall_arm_slide",
      "path": "puppet/wall_arm_slide.json",
      "name": "Flexão de ombro na parede com bola",
      "place": "Em pé",
      "equip": "parede · bola",
      "desc": "Em pé de frente para a parede, posicione uma bola pequena entre a palma da mão e a parede na altura do ombro. Deslize a bola para cima o máximo que conseguir mantendo o braço esticado e depois retorne à posição inicial. Mantenha o corpo alinhado e uma leve pressão contra a bola durante todo o percurso.",
      "also": []
    },
    {
      "slug": "walker_sit_to_stand",
      "path": "puppet/walker_sit_to_stand.json",
      "name": "Sentar para levantar com andador (apoio nos braços da cadeira)",
      "place": "Sentado",
      "equip": "cadeira · andador",
      "desc": "Sente-se na borda da cadeira com os pés afastados e o andador posicionado à frente. Apoie as mãos nos braços da cadeira, incline o tronco para frente e empurre com as pernas para se levantar. Quando estiver quase ereto, leve uma mão de cada vez para as alças do andador para estabilizar a postura.",
      "also": []
    }
  ],
  "lote6": [
    {
      "slug": "wall_calf_stretch",
      "path": "puppet/wall_calf_stretch.json",
      "name": "Alongamento de panturrilha na parede (joelho esticado)",
      "place": "Em pé",
      "equip": "parede",
      "desc": "Em pé de frente para a parede, apoie as mãos e dê um passo para trás com a perna que deseja alongar. Mantendo o calcanhar de trás no chão e o joelho esticado, dobre o joelho da frente levando o corpo em direção à parede. Sinta o alongamento na panturrilha e retorne à posição inicial.",
      "also": [
        "Alongamento de panturrilha na parede",
        "Alongamento de panturrilha na parede (joelho estendido)",
        "Alongamento de panturrilha na parede (gastrocnêmio)",
        "Alongamento de panturrilha com apoio na parede"
      ]
    },
    {
      "slug": "step_heel_drop",
      "path": "puppet/step_heel_drop.json",
      "name": "Panturrilha no degrau",
      "place": "Em pé",
      "equip": "degrau · parede",
      "desc": "Em pé sobre um degrau com os calcanhares para fora, apoie as mãos na parede para equilíbrio. Suba na ponta dos pés o máximo que conseguir e depois desça os calcanhares abaixo do nível do degrau para alongar a panturrilha. Retorne à posição inicial e repita o movimento de forma lenta e controlada.",
      "also": [
        "Flexão plantar bilateral no degrau",
        "Elevação de calcanhar no degrau"
      ]
    },
    {
      "slug": "jab_cross_step",
      "path": "puppet/jab_cross_step.json",
      "name": "Passo à frente com soco alternado",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, dê um passo largo para a frente flexionando levemente os joelhos. Simultaneamente, realize um movimento de soco para a frente com o braço oposto à perna que avançou. Retorne à posição inicial e repita o movimento alternando os lados.",
      "also": [
        "Passo com soco cruzado",
        "Passo à frente com soco cruzado",
        "Passo com soco alternado"
      ]
    },
    {
      "slug": "bird_dog",
      "path": "puppet/bird_dog.json",
      "name": "Perdigueiro",
      "place": "Quatro apoios",
      "equip": "colchonete",
      "desc": "Comece na posição de quatro apoios com as mãos e joelhos no chão. Estenda simultaneamente um braço para a frente e a perna oposta para trás até que fiquem alinhados com o tronco. Retorne lentamente à posição inicial e repita o movimento trocando os lados.",
      "also": []
    },
    {
      "slug": "plank_down_dog",
      "path": "puppet/plank_down_dog.json",
      "name": "Alongamento Dinâmico de Cadeias Anterior e Posterior",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Comece deitado de barriga para baixo com as mãos apoiadas ao lado do peito. Empurre o chão esticando os braços e arqueando as costas para cima enquanto olha para o teto. Em seguida, eleve o quadril em direção ao teto, mantendo braços e pernas esticados para formar um 'V' invertido, retornando suavemente à posição inicial.",
      "also": [
        "Transição de Cão Olhando para Baixo para Cão Olhando para Cima"
      ]
    },
    {
      "slug": "chair_heel_toe",
      "path": "puppet/chair_heel_toe.json",
      "name": "Mobilização de tornozelo sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira com os pés no chão, levante as pontas dos pés e depois os calcanhares. Em seguida, alterne o movimento levantando a ponta de um pé e o calcanhar do outro simultaneamente. Retorne sempre à posição neutra com os pés totalmente apoiados entre as repetições.",
      "also": []
    },
    {
      "slug": "chair_figure_four",
      "path": "puppet/chair_figure_four.json",
      "name": "Alongamento de piriforme sentado (posição de 4)",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado em uma cadeira, cruze uma perna apoiando o tornozelo sobre o joelho oposto. Incline o tronco para frente mantendo as costas retas e pressione levemente o joelho dobrado para baixo. Sustente a posição e retorne devagar.",
      "also": []
    },
    {
      "slug": "lying_arm_reach",
      "path": "puppet/lying_arm_reach.json",
      "name": "Flexão de ombro em supino",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de barriga para cima com as pernas estendidas e os braços ao lado do corpo. Eleve um dos braços mantendo o cotovelo esticado, levando-o em direção ao teto e depois para trás até tocar o chão acima da cabeça. Retorne o braço lentamente para a posição inicial.",
      "also": [
        "Elevação de braços deitado (Flexão de ombro)"
      ]
    },
    {
      "slug": "stick_supine_flexion",
      "path": "puppet/stick_supine_flexion.json",
      "name": "Flexão de ombro assistida com bastão (deitado)",
      "place": "Deitado",
      "equip": "bastão · colchonete",
      "desc": "Deite-se de costas com os joelhos dobrados e segure um bastão com as duas mãos sobre as coxas. Eleve os braços em direção ao teto e continue o movimento até levar o bastão acima da cabeça, tentando encostar no chão atrás de você. Retorne devagar para a posição inicial.",
      "also": [
        "Flexão de ombro assistida com bastão em decúbito dorsal",
        "Flexão de ombro com bastão em supino"
      ]
    },
    {
      "slug": "toe_taps",
      "path": "puppet/toe_taps.json",
      "name": "Toque de calcanhar alternado em supino",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, mantenha as pernas elevadas com joelhos e quadris dobrados em 90 graus. Desça um pé de cada vez até tocar levemente o calcanhar no chão, mantendo a coluna lombar firme contra o solo. Retorne a perna à posição inicial e alterne o movimento com o outro lado.",
      "also": [
        "Estabilização abdominal com toque de calcanhar"
      ]
    },
    {
      "slug": "slow_bicycle",
      "path": "puppet/slow_bicycle.json",
      "name": "Bicicleta no ar",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com os joelhos dobrados e os pés apoiados no chão. Levante as pernas e faça movimentos circulares alternados, como se estivesse pedalando uma bicicleta no ar. Ao terminar, retorne os pés suavemente para a posição inicial.",
      "also": [
        "Bicicleta no ar (supino)"
      ]
    },
    {
      "slug": "figure_four",
      "path": "puppet/figure_four.json",
      "name": "Alongamento de piriforme deitado (Figura 4)",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas e cruze o tornozelo de uma perna sobre o joelho da outra, formando um quatro. Entrelace as mãos atrás da coxa da perna que está apoiada no chão e puxe-a suavemente em direção ao peito. Mantenha a posição sentindo o alongamento na região do glúteo da perna que está cruzada.",
      "also": []
    },
    {
      "slug": "knees_to_chest",
      "path": "puppet/knees_to_chest.json",
      "name": "Abraço de joelhos no peito (bilateral)",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas com os joelhos dobrados, traga ambos os joelhos em direção ao peito simultaneamente. Abrace as pernas com as mãos, puxando-as suavemente para alongar a região lombar. Mantenha a posição por alguns segundos e retorne os pés lentamente para a posição inicial.",
      "also": [
        "Abraço de joelhos bilateral em supino"
      ]
    },
    {
      "slug": "hamstring_stretch",
      "path": "puppet/hamstring_stretch.json",
      "name": "Alongamento de posterior de coxa em supino",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deite-se de costas com os joelhos dobrados e os pés apoiados no chão. Estenda uma das pernas para cima, mantendo a coxa alinhada, até sentir um leve alongamento na parte de trás da coxa. Retorne o pé ao chão de forma controlada e repita com a outra perna.",
      "also": [
        "Alongamento dinâmico de isquiotibiais em supino"
      ]
    },
    {
      "slug": "prone_knee_flexion",
      "path": "puppet/prone_knee_flexion.json",
      "name": "Flexão de joelho em decúbito prono",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deite-se de barriga para baixo com as pernas estendidas e a testa apoiada em uma toalha dobrada. Dobre um dos joelhos lentamente, elevando o pé em direção ao teto até formar um ângulo de 90 graus. Retorne a perna à posição inicial de forma controlada e repita o movimento.",
      "also": [
        "Flexão de joelho em prono (fase excêntrica)"
      ]
    },
    {
      "slug": "prone_superman",
      "path": "puppet/prone_superman.json",
      "name": "Extensão lombar em prono (Super-homem)",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de barriga para baixo com braços e pernas esticados, levante simultaneamente o peito, os braços e as pernas do chão. Mantenha a posição por alguns segundos sentindo a musculatura das costas trabalhar. Retorne devagar à posição inicial relaxando o corpo no colchonete.",
      "also": []
    }
  ],
  "lote7": [
    {
      "slug": "arm_pendulum",
      "path": "puppet/arm_pendulum.json",
      "name": "Pêndulo dos braços",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, deixa os braços soltos e balança-os para a frente e para trás como um pêndulo, relaxando os ombros.",
      "also": [
        "Exercício pendular de ombro (adução e abdução)",
        "Pêndulo de Codman com peso (flexão e extensão)"
      ]
    },
    {
      "slug": "back_leg_raise",
      "path": "puppet/back_leg_raise.json",
      "name": "Extensão de quadril em pé",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com o tronco levemente inclinado à frente, eleva uma perna estendida para trás contraindo o glúteo.",
      "also": []
    },
    {
      "slug": "balance_leg_swing_front_back",
      "path": "puppet/balance_leg_swing_front_back.json",
      "name": "Balanço da perna à frente e atrás",
      "place": "Em pé",
      "equip": "",
      "desc": "Apoiado numa perna, balança a outra perna à frente e atrás num movimento suave, mantendo o tronco ereto.",
      "also": [
        "Equilíbrio unipodal com balanço de perna"
      ]
    },
    {
      "slug": "balance_single_leg_stand",
      "path": "puppet/balance_single_leg_stand.json",
      "name": "Apoio unipodal com joelho flexionado",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, tira um pé do chão com o joelho flexionado e fixa o olhar num ponto à frente. Troca de perna.",
      "also": [
        "Equilíbrio unipodal"
      ]
    },
    {
      "slug": "balance_slow_march",
      "path": "puppet/balance_slow_march.json",
      "name": "Marcha lenta com pausa",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, eleva um joelho e faz uma pausa no alto. Abaixa sem bater o pé e eleva a outra perna.",
      "also": []
    },
    {
      "slug": "balance_toe_heel_rock",
      "path": "puppet/balance_toe_heel_rock.json",
      "name": "Balanço pontas e calcanhares",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, sobe devagar na ponta dos pés. Desce e eleva as pontas, ficando apoiado nos calcanhares.",
      "also": []
    },
    {
      "slug": "butt_kick_walk",
      "path": "puppet/butt_kick_walk.json",
      "name": "Marcha com calcanhar ao glúteo",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, flexiona um joelho levando o calcanhar em direção ao glúteo e alterna as pernas num ritmo constante, com os braços acompanhando.",
      "also": [
        "Corrida estacionária com calcanhar no glúteo"
      ]
    },
    {
      "slug": "heel_to_toe_stand",
      "path": "puppet/heel_to_toe_stand.json",
      "name": "Postura em tandem",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, coloca um pé exatamente à frente do outro, calcanhar encostado nos dedos, com os braços levemente abertos. Troca o pé da frente.",
      "also": [
        "Equilíbrio em Tandem (Um pé à frente do outro)"
      ]
    },
    {
      "slug": "heel_to_toe_walk_in_place",
      "path": "puppet/heel_to_toe_walk_in_place.json",
      "name": "Marcha tandem no lugar",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com os braços levemente abertos, eleva um pé e o apoia exatamente à frente do outro, calcanhar encostado nos dedos, alternando os pés.",
      "also": [
        "Marcha tandem",
        "Caminhada pé ante pé (Tandem)",
        "Marcha tandem (pé ante pé)"
      ]
    },
    {
      "slug": "high_knee_march",
      "path": "puppet/high_knee_march.json",
      "name": "Marcha com joelhos altos",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, eleva bem um joelho e depois o outro, com os braços acompanhando em oposição às pernas.",
      "also": [
        "Marcha do soldado",
        "Caminhada com joelhos altos"
      ]
    },
    {
      "slug": "march_in_place",
      "path": "puppet/march_in_place.json",
      "name": "Marcha estacionária",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé e olhando à frente, eleva um joelho e depois o outro, como numa caminhada, balançando os braços em oposição às pernas.",
      "also": [
        "Marcha estacionária com balanço de braços",
        "Caminhada rápida estacionária com balanço de braços",
        "Marcha com elevação de joelhos e braço oposto"
      ]
    },
    {
      "slug": "high_knees",
      "path": "puppet/high_knees.json",
      "name": "Corrida no lugar com joelhos altos",
      "place": "Em pé",
      "equip": "",
      "desc": "Corre no lugar levando os joelhos à altura do quadril, com os braços acompanhando o movimento.",
      "also": [
        "Corrida estacionária com joelhos altos"
      ]
    },
    {
      "slug": "jog_in_place",
      "path": "puppet/jog_in_place.json",
      "name": "Corrida no lugar",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, simula uma corrida sem sair do lugar, elevando os joelhos alternadamente e balançando os braços.",
      "also": []
    },
    {
      "slug": "hops",
      "path": "puppet/hops.json",
      "name": "Saltitos no lugar",
      "place": "Em pé",
      "equip": "",
      "desc": "Faz saltos pequenos no lugar, aterrissando macio com os dois pés.",
      "also": [
        "Saltitos no lugar com variação de altura"
      ]
    },
    {
      "slug": "jump_rope_scissor",
      "path": "puppet/jump_rope_scissor.json",
      "name": "Saltos em tesoura como na corda",
      "place": "Em pé",
      "equip": "",
      "desc": "Com as mãos como se segurasse uma corda de pular, dá pequenos saltos alternando os pés à frente e atrás.",
      "also": [
        "Pulo de tesoura simulando corda"
      ]
    },
    {
      "slug": "toe_heel_rock_supported",
      "path": "puppet/toe_heel_rock_supported.json",
      "name": "Balanço pontas e calcanhares com apoio",
      "place": "Em pé",
      "equip": "cadeira",
      "desc": "Em pé, com as mãos no encosto de uma cadeira, sobe devagar na ponta dos pés, desce e eleva as pontas, ficando nos calcanhares.",
      "also": [
        "Balanço anteroposterior em pé com apoio",
        "Flexão plantar e dorsiflexão em pé com apoio"
      ]
    },
    {
      "slug": "fast_feet_small",
      "path": "puppet/fast_feet_small.json",
      "name": "Passos rápidos no lugar",
      "place": "Em pé",
      "equip": "",
      "desc": "Com os joelhos soltos e o tronco levemente inclinado, dá passos curtos e rápidos no lugar, na ponta dos pés, movendo os braços no ritmo.",
      "also": [
        "Passos curtos e rápidos no lugar"
      ]
    }
  ],
  "lote8": [
    {
      "slug": "forward_lunge",
      "path": "puppet/forward_lunge.json",
      "name": "Avanço à frente",
      "place": "Em pé",
      "equip": "",
      "desc": "Dá um passo à frente e desce o joelho de trás em direção ao chão, com o tronco ereto. Empurra com a perna da frente para voltar e troca de perna.",
      "also": [
        "Afundo",
        "Avanço frontal",
        "Avanço"
      ]
    },
    {
      "slug": "backward_lunge",
      "path": "puppet/backward_lunge.json",
      "name": "Avanço para trás com mãos na cintura",
      "place": "Em pé",
      "equip": "",
      "desc": "Com as mãos na cintura, dá um passo para trás e desce o joelho de trás. Volta à posição inicial e troca de perna.",
      "also": [
        "Afundo reverso com mãos na cintura",
        "Afundo reverso",
        "Afundo reverso alternado"
      ]
    },
    {
      "slug": "front_kicks",
      "path": "puppet/front_kicks.json",
      "name": "Chute frontal",
      "place": "Em pé",
      "equip": "",
      "desc": "Eleva o joelho e estende a perna à frente num chute controlado. Volta e troca de perna.",
      "also": [
        "Chute frontal com perna estendida"
      ]
    },
    {
      "slug": "punches",
      "path": "puppet/punches.json",
      "name": "Socos alternados",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com os joelhos soltos e as mãos junto ao queixo, soca à frente com uma mão e depois com a outra, sem travar o cotovelo.",
      "also": [
        "Socos frontais alternados"
      ]
    },
    {
      "slug": "hinge_reach",
      "path": "puppet/hinge_reach.json",
      "name": "Inclinar o tronco para alcançar o chão, em pé",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, inclina o tronco à frente dobrando o quadril para alcançar um objeto no chão e volta à posição ereta.",
      "also": [
        "Pegar objeto no chão com inclinação de tronco"
      ]
    },
    {
      "slug": "hinge_reach_forward",
      "path": "puppet/hinge_reach_forward.json",
      "name": "Inclinação do quadril com alcance à frente",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, inclina o tronco à frente a partir do quadril, levando os braços estendidos à frente, e volta à posição ereta.",
      "also": [
        "Alcance frontal em pé"
      ]
    },
    {
      "slug": "hinge_row_no_weight",
      "path": "puppet/hinge_row_no_weight.json",
      "name": "Remada com o tronco inclinado",
      "place": "Em pé",
      "equip": "halter",
      "desc": "Com o tronco inclinado à frente e as costas retas, puxa os halteres em direção ao abdômen, apertando as escápulas, e desce devagar.",
      "also": [
        "Remada cortador de grama"
      ]
    },
    {
      "slug": "bend_and_reach",
      "path": "puppet/bend_and_reach.json",
      "name": "Agachar e alcançar",
      "place": "Em pé",
      "equip": "",
      "desc": "Agacha levando as mãos em direção ao chão e depois sobe alcançando acima da cabeça.",
      "also": [
        "Agachamento com alcance de braços"
      ]
    },
    {
      "slug": "knee_lift_pull_down",
      "path": "puppet/knee_lift_pull_down.json",
      "name": "Elevação de joelho com puxada dos braços",
      "place": "Em pé",
      "equip": "",
      "desc": "Com os braços estendidos acima da cabeça, eleva um joelho e puxa os braços para baixo em direção a ele. Volta a estender os braços.",
      "also": [
        "Simulação de quebra de bastão"
      ]
    },
    {
      "slug": "single_leg_arms_overhead",
      "path": "puppet/single_leg_arms_overhead.json",
      "name": "Apoio unipodal com elevação dos braços",
      "place": "Em pé",
      "equip": "",
      "desc": "Apoiado numa perna, eleva os braços acima da cabeça e abaixa, mantendo o equilíbrio. Troca de perna.",
      "also": [
        "Equilíbrio unipodal com elevação alternada de braços"
      ]
    },
    {
      "slug": "single_leg_mini_hinge",
      "path": "puppet/single_leg_mini_hinge.json",
      "name": "Inclinação à frente numa perna (pegar um objeto)",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé numa perna, inclina o tronco à frente com as costas retas como se fosse pegar um objeto no chão e volta.",
      "also": [
        "Pegar objeto no chão em apoio unipodal"
      ]
    },
    {
      "slug": "standing_back_extension",
      "path": "puppet/standing_back_extension.json",
      "name": "Extensão lombar em pé",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, com as mãos na parte baixa das costas, eleva o peito e inclina o tronco levemente para trás. Mantém 2 segundos e volta.",
      "also": [
        "Extensão de coluna em pé",
        "Extensão de coluna lombar em pé"
      ]
    },
    {
      "slug": "standing_forward_fold_soft",
      "path": "puppet/standing_forward_fold_soft.json",
      "name": "Flexão do tronco em pé com joelhos soltos",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, inclina o tronco à frente deixando os braços pendurados em direção ao chão, sustenta e sobe devagar.",
      "also": [
        "Alongamento de isquiotibiais e banda iliotibial com pernas cruzadas"
      ]
    },
    {
      "slug": "posture_reset",
      "path": "puppet/posture_reset.json",
      "name": "Correção postural em pé",
      "place": "Em pé",
      "equip": "",
      "desc": "Começa curvado, com as costas arredondadas e a cabeça à frente. Cresce, recolhe o queixo e leva os ombros para trás, mantendo 3 segundos.",
      "also": [
        "Encontrando a postura neutra em pé",
        "Correção Postural Sentada",
        "Correção postural sentada"
      ]
    },
    {
      "slug": "round_and_open",
      "path": "puppet/round_and_open.json",
      "name": "Arredondar e abrir o tronco",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, arredonda as costas como se abraçasse uma bola grande e abaixa o queixo. Depois abre os braços para os lados e para trás, elevando o peito.",
      "also": [
        "Abraço cruzado com abertura de braços"
      ]
    },
    {
      "slug": "warrior_1_gentle",
      "path": "puppet/warrior_1_gentle.json",
      "name": "Afundo com elevação dos braços",
      "place": "Em pé",
      "equip": "",
      "desc": "Dá um passo grande à frente com a perna de trás estendida, flexiona o joelho da frente sobre o tornozelo e eleva os braços. Volta e troca de perna.",
      "also": [
        "Avanço com elevação de braço"
      ]
    }
  ],
  "lote9": [
    {
      "slug": "chair_forward_fold",
      "path": "puppet/chair_forward_fold.json",
      "name": "Alongamento das costas inclinando à frente, sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado, inclina o tronco à frente levando os braços em direção ao chão e sustenta, sentindo o alongamento nas costas.",
      "also": [
        "Alongamento de ombros e costas sentado com apoio na mesa"
      ]
    },
    {
      "slug": "floor_long_sit_forward_fold",
      "path": "puppet/floor_long_sit_forward_fold.json",
      "name": "Flexão do tronco sentado com pernas estendidas",
      "place": "Sentado",
      "equip": "colchonete",
      "desc": "Sentado no chão, com as pernas estendidas à frente, leva as mãos em direção aos pés inclinando o tronco a partir do quadril.",
      "also": [
        "Alongamento de cadeia posterior sentado com pernas estendidas"
      ]
    },
    {
      "slug": "seated_spinal_twist",
      "path": "puppet/seated_spinal_twist.json",
      "name": "Rotação de tronco sentado com auxílio das mãos",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado e ereto, com os pés no chão, gira o tronco para um lado com uma mão no joelho oposto, crescendo ao inspirar e girando um pouco mais ao expirar. Repete do outro lado.",
      "also": [
        "Rotação de tronco sentado com auxílio"
      ]
    },
    {
      "slug": "chair_dips_kick_out",
      "path": "puppet/chair_dips_kick_out.json",
      "name": "Mergulho na cadeira com chute à frente",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Com as mãos na borda de uma cadeira, desce e sobe o quadril dobrando os cotovelos e, ao subir, estica uma perna à frente, alternando.",
      "also": [
        "Mergulho na cadeira com chute alternado"
      ]
    },
    {
      "slug": "chair_knee_flexion_assist",
      "path": "puppet/chair_knee_flexion_assist.json",
      "name": "Flexão do joelho assistida pela outra perna, sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado, dobra o joelho levando o pé para baixo da cadeira e usa o tornozelo da outra perna para empurrar um pouco mais. Sustenta e relaxa.",
      "also": [
        "Flexão de joelho sentada com auxílio"
      ]
    },
    {
      "slug": "chair_slump",
      "path": "puppet/chair_slump.json",
      "name": "Mobilização neural em slump, sentado",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Sentado, curva o tronco e abaixa a cabeça, depois estica um joelho e puxa a ponta do pé para cima até sentir uma leve tensão, voltando devagar.",
      "also": [
        "Mobilização do nervo isquiático sentado (Slump Test)"
      ]
    },
    {
      "slug": "chair_stick_flexion_vertical",
      "path": "puppet/chair_stick_flexion_vertical.json",
      "name": "Flexão do ombro assistida com bastão vertical, sentado",
      "place": "Sentado",
      "equip": "cadeira · bastão",
      "desc": "Sentado, segura o bastão na vertical com a mão do braço a exercitar no topo e, com a outra mão, empurra o bastão para cima elevando o braço o mais alto possível. Desce devagar.",
      "also": [
        "Flexão de ombro assistida com bastão (sentado)"
      ]
    },
    {
      "slug": "chair_triceps_dips",
      "path": "puppet/chair_triceps_dips.json",
      "name": "Mergulho de tríceps na cadeira",
      "place": "Sentado",
      "equip": "cadeira",
      "desc": "Com as mãos na borda de uma cadeira firme e os pés no chão, dobra os cotovelos descendo o quadril à frente do assento e empurra para subir.",
      "also": [
        "Mergulho na cadeira"
      ]
    },
    {
      "slug": "kneel_sit_to_tall_kneel",
      "path": "puppet/kneel_sit_to_tall_kneel.json",
      "name": "De sentado nos calcanhares para ajoelhado",
      "place": "Ajoelhado",
      "equip": "",
      "desc": "Sentado sobre os calcanhares com os braços cruzados, sobe até ficar ajoelhado com o quadril estendido e desce devagar.",
      "also": [
        "Ajoelhado para ajoelhado alto com braços cruzados"
      ]
    },
    {
      "slug": "genie_sit",
      "path": "puppet/genie_sit.json",
      "name": "Inclinação para trás ajoelhado",
      "place": "Ajoelhado",
      "equip": "",
      "desc": "Ajoelhado com o corpo reto e os braços cruzados, inclina o corpo inteiro para trás a partir dos joelhos e volta.",
      "also": [
        "Inclinação posterior ajoelhada (Genie Sit)"
      ]
    },
    {
      "slug": "cross_knee_tap",
      "path": "puppet/cross_knee_tap.json",
      "name": "Joelho cruzado à mão oposta",
      "place": "Em pé",
      "equip": "",
      "desc": "Em pé, eleva um braço na diagonal. Sobe o joelho oposto em direção ao centro do corpo e leva a mão até ele. Alterna os lados.",
      "also": [
        "Elevação de joelho alternada com toque de mão"
      ]
    },
    {
      "slug": "triceps_kickback",
      "path": "puppet/triceps_kickback.json",
      "name": "Extensão de cotovelo inclinado",
      "place": "Em pé",
      "equip": "",
      "desc": "Com o tronco inclinado à frente e os cotovelos junto ao corpo, estende os cotovelos levando as mãos para trás e volta devagar.",
      "also": [
        "Extensão de cotovelo em pé com apoio"
      ]
    }
  ],
  "lote10": [
    {
      "slug": "floor_butterfly_stretch",
      "path": "puppet/floor_butterfly_stretch.json",
      "name": "Alongamento borboleta",
      "place": "Sentado",
      "equip": "colchonete",
      "desc": "Sentado no chão, junta as solas dos pés e deixa os joelhos caírem para os lados, segurando os pés com as mãos e mantendo o tronco ereto.",
      "also": [
        "Alongamento de adutores em borboleta"
      ]
    },
    {
      "slug": "floor_head_to_knee_easy",
      "path": "puppet/floor_head_to_knee_easy.json",
      "name": "Alongamento de posteriores com uma perna estendida",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Sentado no chão, com uma perna estendida e o outro pé junto à parte interna da coxa, gira o tronco para a perna estendida e inclina à frente. Troca de lado.",
      "also": [
        "Alongamento de isquiotibiais sentado"
      ]
    },
    {
      "slug": "reclined_butterfly",
      "path": "puppet/reclined_butterfly.json",
      "name": "Borboleta deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, junta as solas dos pés e deixa os joelhos caírem para os lados, com os braços soltos ao lado do corpo, respirando com calma.",
      "also": [
        "Alongamento de adutores de quadril em supino"
      ]
    },
    {
      "slug": "supine_marching",
      "path": "puppet/supine_marching.json",
      "name": "Marcha deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, com os joelhos flexionados, eleva um pé até o joelho ficar sobre o quadril, mantendo a flexão. Desce sem bater e troca de perna.",
      "also": [
        "Marcha deitada com joelhos dobrados",
        "Marcha deitada com ativação abdominal",
        "Estabilização lombar no rolo de espuma em supino"
      ]
    },
    {
      "slug": "flutter_kicks",
      "path": "puppet/flutter_kicks.json",
      "name": "Batida de pernas deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas com as pernas esticadas e um pouco elevadas, alterna pequenas batidas para cima e para baixo.",
      "also": [
        "Chutes alternados em supino"
      ]
    },
    {
      "slug": "leg_raises",
      "path": "puppet/leg_raises.json",
      "name": "Elevação das pernas esticadas",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, eleva as duas pernas esticadas juntas e desce devagar sem deixar a lombar arquear.",
      "also": [
        "Elevação de pernas estendidas"
      ]
    },
    {
      "slug": "supine_bent_leg_lift",
      "path": "puppet/supine_bent_leg_lift.json",
      "name": "Elevação das pernas dobradas deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas com os joelhos dobrados, eleva as duas pernas até quadris e joelhos ficarem a 90 graus e desce devagar.",
      "also": [
        "Flexão bilateral de quadril deitado"
      ]
    },
    {
      "slug": "supine_pullover",
      "path": "puppet/supine_pullover.json",
      "name": "Pullover deitado",
      "place": "Deitado",
      "equip": "cama",
      "desc": "Deitado de costas na cama, com os braços apontando para o teto, leva os braços estendidos acima da cabeça e volta.",
      "also": [
        "Pullover de ombro em supino"
      ]
    },
    {
      "slug": "supine_pullover_dumbbell",
      "path": "puppet/supine_pullover_dumbbell.json",
      "name": "Pullover deitado com halteres",
      "place": "Deitado",
      "equip": "cama · halter",
      "desc": "Deitado de costas na cama, com os halteres apontando para o teto, leva os braços acima da cabeça e volta devagar.",
      "also": [
        "Pullover com halter em decúbito dorsal",
        "Pulôver unilateral em supino com halter",
        "Flexão de ombro a 90° com halter em supino"
      ]
    },
    {
      "slug": "supine_sciatic_glide",
      "path": "puppet/supine_sciatic_glide.json",
      "name": "Mobilização do nervo ciático, deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, segura a coxa com o quadril a 90° e estica o joelho puxando a ponta do pé, depois dobra e aponta o pé.",
      "also": [
        "Mobilização neural do nervo ciático (deslizamento)"
      ]
    },
    {
      "slug": "supine_shoulder_flexion_90",
      "path": "puppet/supine_shoulder_flexion_90.json",
      "name": "Flexão de ombro a 90° deitado",
      "place": "Deitado",
      "equip": "cama",
      "desc": "Deitado de costas na cama, eleva um braço estendido até apontar para o teto e desce devagar.",
      "also": [
        "Flexão de ombro a 90° em decúbito dorsal",
        "Flexão de ombro assistida em decúbito dorsal"
      ]
    },
    {
      "slug": "supine_straight_leg_lower",
      "path": "puppet/supine_straight_leg_lower.json",
      "name": "Descida da perna esticada deitado",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas, traz um joelho ao peito segurando a coxa, estica a perna para o alto e desce devagar com ela reta até o chão, mantendo o abdômen contraído.",
      "also": [
        "Estabilização de tronco com extensão de perna em supino"
      ]
    },
    {
      "slug": "stick_supine_curl",
      "path": "puppet/stick_supine_curl.json",
      "name": "Flexão de cotovelos com bastão, deitado",
      "place": "Deitado",
      "equip": "bastão · colchonete",
      "desc": "Deitado de costas com os joelhos dobrados e o bastão nas mãos com os braços para o teto, dobra os cotovelos trazendo o bastão até o peito e estica de volta.",
      "also": [
        "Flexão de cotovelo assistida com bastão em decúbito dorsal"
      ]
    },
    {
      "slug": "stick_supine_ir_stretch_90",
      "path": "puppet/stick_supine_ir_stretch_90.json",
      "name": "Alongamento dos rotadores internos com bastão, braço a 90°, deitado",
      "place": "Deitado",
      "equip": "bastão · colchonete",
      "desc": "Deitado de costas com o braço aberto e o cotovelo a 90°, segura o bastão com as duas mãos e, com a mão do outro lado, empurra girando o antebraço para trás. Sustenta e volta.",
      "also": [
        "Alongamento de rotadores internos do ombro com bastão (90/90)"
      ]
    },
    {
      "slug": "slr_external_rotation",
      "path": "puppet/slr_external_rotation.json",
      "name": "Elevação da perna estendida com rotação externa",
      "place": "Deitado",
      "equip": "cama",
      "desc": "Deitado de costas na cama, com um joelho dobrado, gira a outra perna para fora e eleva-a estendida até a altura do joelho dobrado. Desce devagar.",
      "also": [
        "Elevação de perna estendida com rotação externa"
      ]
    }
  ],
  "lote11": [
    {
      "slug": "push_up",
      "path": "puppet/push_up.json",
      "name": "Flexão de braços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Em prancha, com as mãos no chão abaixo dos ombros e apoio na ponta dos pés, dobra os cotovelos e desce o peito. Empurra de volta, com o corpo em linha.",
      "also": [
        "Flexão de braços com mãos desalinhadas",
        "Prancha dinâmica (subida e descida)",
        "Flexão de braços com deslocamento lateral"
      ]
    },
    {
      "slug": "knee_push_up",
      "path": "puppet/knee_push_up.json",
      "name": "Flexão de braços com joelhos apoiados",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Com as mãos e os joelhos no chão e o corpo alinhado da cabeça aos joelhos, desce o peito dobrando os cotovelos e empurra de volta.",
      "also": [
        "Flexão de braços com apoio dos joelhos",
        "Flexão de braços diamante com joelhos apoiados"
      ]
    },
    {
      "slug": "mountain_climber",
      "path": "puppet/mountain_climber.json",
      "name": "Escalador",
      "place": "Quatro apoios",
      "equip": "colchonete",
      "desc": "Em prancha sobre as mãos, leva um joelho em direção ao peito e volta, alternando as pernas num ritmo constante.",
      "also": []
    },
    {
      "slug": "thread_the_needle",
      "path": "puppet/thread_the_needle.json",
      "name": "Passar a linha na agulha",
      "place": "Quatro apoios",
      "equip": "colchonete",
      "desc": "Em quatro apoios, desliza um braço por baixo do corpo para o outro lado, deixando o ombro descer em direção ao chão. Volta e troca de lado.",
      "also": [
        "Rotação de tronco em quatro apoios (Passar a linha na agulha)"
      ]
    },
    {
      "slug": "prone_opposite_lift",
      "path": "puppet/prone_opposite_lift.json",
      "name": "Elevação de braço e perna opostos de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços, com os braços à frente, eleva um braço e a perna oposta um pouco do chão. Desce e troca de lado.",
      "also": [
        "Elevação de braço e perna opostos em prono"
      ]
    },
    {
      "slug": "prone_swimmers",
      "path": "puppet/prone_swimmers.json",
      "name": "Nado de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços, com os braços à frente e o peito levemente elevado, alterna braços e pernas opostos para cima e para baixo em movimentos curtos e rápidos.",
      "also": [
        "Nado em decúbito ventral"
      ]
    },
    {
      "slug": "prone_w_squeeze",
      "path": "puppet/prone_w_squeeze.json",
      "name": "Retração escapular em W de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços, com os cotovelos flexionados para os lados formando um W, eleva cotovelos e mãos e aproxima as escápulas. Mantém 2 segundos e desce.",
      "also": [
        "Retração escapular em prono",
        "Retração escapular em prono com braços em L",
        "Retração escapular em prono com braços a 90 graus"
      ]
    },
    {
      "slug": "prone_y_raise",
      "path": "puppet/prone_y_raise.json",
      "name": "Elevação em Y de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços, com os braços abertos em Y e os polegares para cima, eleva os braços um pouco, aproxima as escápulas e desce.",
      "also": [
        "Retração escapular em Y em decúbito ventral"
      ]
    },
    {
      "slug": "prone_m_raise",
      "path": "puppet/prone_m_raise.json",
      "name": "Elevação dos braços em M de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços com os braços baixos ao lado do corpo e as palmas para baixo, eleva os braços e desce devagar.",
      "also": [
        "Retração escapular em prono com elevação de braços"
      ]
    },
    {
      "slug": "prone_shoulder_extension",
      "path": "puppet/prone_shoulder_extension.json",
      "name": "Extensão dos ombros de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços com os braços ao longo do corpo, eleva os dois braços em direção ao teto e desce devagar.",
      "also": [
        "Extensão de ombro e retração escapular em prono",
        "Extensão de ombro com retração escapular em prono"
      ]
    },
    {
      "slug": "prone_t_raise",
      "path": "puppet/prone_t_raise.json",
      "name": "Elevação dos braços em T de bruços",
      "place": "De bruços",
      "equip": "colchonete",
      "desc": "Deitado de bruços com os braços abertos para os lados, eleva os braços aproximando as escápulas e desce devagar.",
      "also": [
        "Retração escapular em prono (posição T) com palmas para frente",
        "Extensão de ombros em T no solo"
      ]
    },
    {
      "slug": "v_sit_up",
      "path": "puppet/v_sit_up.json",
      "name": "Abdominal em V",
      "place": "Deitado",
      "equip": "colchonete",
      "desc": "Deitado de costas com braços e pernas esticados, eleva o tronco e as pernas ao mesmo tempo formando um V e desce devagar.",
      "also": []
    }
  ],
  "lote12": [
    {
      "slug": "step_up_alternate",
      "path": "puppet/step_up_alternate.json",
      "name": "Subida no degrau alternando as pernas",
      "place": "Em pé",
      "equip": "degrau",
      "desc": "De frente para o degrau, sobe com um pé e leva o outro. Desce na mesma ordem e, na volta seguinte, começa com a outra perna.",
      "also": [
        "Subida e descida de degrau",
        "Subida no step alternada",
        "Subida e descida no step com olhos fechados"
      ]
    },
    {
      "slug": "step_down_backward",
      "path": "puppet/step_down_backward.json",
      "name": "Descida do degrau para trás",
      "place": "Em pé",
      "equip": "degrau",
      "desc": "Em pé sobre o degrau, dobra o joelho de apoio e leva o outro pé para trás até tocar o chão. Volta a subir esticando a perna de apoio.",
      "also": [
        "Descida de degrau (Step down)"
      ]
    },
    {
      "slug": "step_fast_feet",
      "path": "puppet/step_fast_feet.json",
      "name": "Troca rápida de pés no degrau",
      "place": "Em pé",
      "equip": "degrau",
      "desc": "Com um pé sobre o degrau e o outro no chão, troca os pés com um pequeno salto num ritmo rápido.",
      "also": [
        "Troca lateral rápida de pés no step",
        "Troca de pés no step com salto",
        "Salto tesoura no step"
      ]
    },
    {
      "slug": "stick_chest_lift",
      "path": "puppet/stick_chest_lift.json",
      "name": "Elevação do bastão do peito até acima da cabeça",
      "place": "Em pé",
      "equip": "bastão",
      "desc": "Em pé, segura um bastão na altura do peito e empurra para cima até esticar os braços acima da cabeça, voltando devagar ao peito.",
      "also": [
        "Elevação de bastão supinado"
      ]
    },
    {
      "slug": "stick_curl",
      "path": "puppet/stick_curl.json",
      "name": "Flexão de cotovelos com bastão, em pé",
      "place": "Em pé",
      "equip": "bastão",
      "desc": "Em pé, segura um bastão com as palmas para cima e os braços esticados, dobra os cotovelos trazendo o bastão em direção aos ombros e estica de volta devagar.",
      "also": [
        "Flexão e extensão de cotovelo com bastão em pé",
        "Flexão de cotovelo com bastão em pé"
      ]
    },
    {
      "slug": "stick_flexion_90",
      "path": "puppet/stick_flexion_90.json",
      "name": "Elevação do bastão até a altura dos ombros",
      "place": "Em pé",
      "equip": "bastão",
      "desc": "Em pé, segura um bastão à frente das coxas e eleva os braços esticados até a altura dos ombros, descendo devagar sem encolher os ombros.",
      "also": [
        "Flexão de ombro com bastão (palmas para cima)"
      ]
    },
    {
      "slug": "wall_soleus_stretch",
      "path": "puppet/wall_soleus_stretch.json",
      "name": "Alongamento do sóleo na parede",
      "place": "Em pé",
      "equip": "parede",
      "desc": "Com as mãos na parede e uma perna atrás, mantém o calcanhar de trás no chão, dobra os dois joelhos e inclina o corpo à frente.",
      "also": [
        "Alongamento do sóleo em pé com apoio na parede",
        "Alongamento de sóleo em pé com apoio na parede",
        "Alongamento de sóleo em pé com apoio"
      ]
    },
    {
      "slug": "wall_ball_circles",
      "path": "puppet/wall_ball_circles.json",
      "name": "Rolar a bola na parede em pequenos círculos",
      "place": "Em pé",
      "equip": "parede · bola",
      "desc": "Em pé de frente para a parede, com a mão sobre a bola na altura do ombro, rola a bola para cima, para baixo e para os lados em movimentos curtos.",
      "also": [
        "Estabilização escapular com bola na parede (vertical)"
      ]
    },
    {
      "slug": "tuck_jump",
      "path": "puppet/tuck_jump.json",
      "name": "Salto grupado",
      "place": "Em pé",
      "equip": "",
      "desc": "De pé, faz um pequeno agachamento e salta para cima levando os joelhos em direção ao peito, aterrissando com os joelhos flexionados.",
      "also": [
        "Salto com joelhos ao peito",
        "Salto com joelhos no peito (Tuck Jump)",
        "Agachamento com Salto Grupado"
      ]
    }
  ]
,
  "lote13": [
  {
    "slug": "ball_bridge",
    "path": "puppet/ball_bridge.json",
    "name": "Ponte com os calcanhares na bola suíça",
    "place": "Deitado",
    "equip": "bola · colchonete",
    "desc": "Deitado de costas com os calcanhares sobre a bola, eleva o quadril até alinhar ombros, quadril e calcanhares, e desce devagar.",
    "also": []
  },
  {
    "slug": "ball_single_leg_bridge",
    "path": "puppet/ball_single_leg_bridge.json",
    "name": "Ponte unilateral na bola suíça",
    "place": "Deitado",
    "equip": "bola · colchonete",
    "desc": "Deitado de costas com um calcanhar na bola e a outra perna esticada para o alto, eleva o quadril mantendo o equilíbrio e desce devagar.",
    "also": []
  },
  {
    "slug": "ball_hamstring_curl",
    "path": "puppet/ball_hamstring_curl.json",
    "name": "Flexão de joelhos com os pés na bola suíça",
    "place": "Deitado",
    "equip": "bola · colchonete",
    "desc": "Com os calcanhares na bola e o quadril elevado, dobra os joelhos trazendo a bola para perto do corpo e estica as pernas de novo, sem baixar o quadril.",
    "also": []
  },
  {
    "slug": "ball_single_leg_curl",
    "path": "puppet/ball_single_leg_curl.json",
    "name": "Flexão de joelho unilateral na bola suíça",
    "place": "Deitado",
    "equip": "bola · colchonete",
    "desc": "Com o quadril elevado e uma perna esticada para o alto, a outra perna dobra o joelho puxando a bola para perto do corpo e volta a esticar.",
    "also": []
  },
  {
    "slug": "ball_roll_supine",
    "path": "puppet/ball_roll_supine.json",
    "name": "Rolar a bola com um calcanhar, deitado",
    "place": "Deitado",
    "equip": "bola · colchonete",
    "desc": "Deitado de costas com um pé no chão e o outro calcanhar na bola, dobra o joelho trazendo a bola para perto e empurra de volta esticando a perna.",
    "also": []
  },
  {
    "slug": "ball_slr_opposite",
    "path": "puppet/ball_slr_opposite.json",
    "name": "Elevação da perna esticada com o outro pé na bola",
    "place": "Deitado",
    "equip": "bola · colchonete",
    "desc": "Deitado de costas com um pé apoiado na bola e o joelho dobrado, eleva a outra perna esticada alguns centímetros e desce devagar.",
    "also": []
  },
  {
    "slug": "ball_plank_forearms",
    "path": "puppet/ball_plank_forearms.json",
    "name": "Prancha com os antebraços na bola suíça",
    "place": "De bruços",
    "equip": "bola · colchonete",
    "desc": "Ajoelhado com os antebraços sobre a bola, estica as pernas até ficar em prancha com o corpo alinhado, sustenta e volta a apoiar os joelhos.",
    "also": []
  },
  {
    "slug": "ball_plank_tuck",
    "path": "puppet/ball_plank_tuck.json",
    "name": "Prancha com as canelas na bola, joelhos ao peito",
    "place": "De bruços",
    "equip": "bola · colchonete",
    "desc": "Em prancha com as mãos no chão e as canelas sobre a bola, puxa os joelhos em direção ao peito rolando a bola e estica as pernas de volta.",
    "also": []
  },
  {
    "slug": "ball_plank_single_knee",
    "path": "puppet/ball_plank_single_knee.json",
    "name": "Prancha com as canelas na bola, um joelho ao peito",
    "place": "De bruços",
    "equip": "bola · colchonete",
    "desc": "Em prancha com as mãos no chão e as canelas sobre a bola, leva um joelho em direção ao peito, devolve a perna à bola e alterna.",
    "also": []
  },
  {
    "slug": "ball_rollout_kneeling",
    "path": "puppet/ball_rollout_kneeling.json",
    "name": "Rolamento à frente na bola suíça, ajoelhado",
    "place": "Ajoelhado",
    "equip": "bola",
    "desc": "Ajoelhado com os antebraços na bola, rola a bola para a frente inclinando o corpo em linha reta e volta puxando com o abdômen.",
    "also": []
  },
  {
    "slug": "ball_kneeling_arm_lift",
    "path": "puppet/ball_kneeling_arm_lift.json",
    "name": "Ajoelhado com as mãos na bola, elevação de um braço",
    "place": "Ajoelhado",
    "equip": "bola",
    "desc": "Ajoelhado com as mãos sobre a bola suíça à frente, eleva um braço esticado acima da cabeça, devolve a mão à bola e alterna.",
    "also": []
  },
  {
    "slug": "towel_calf_stretch",
    "path": "puppet/towel_calf_stretch.json",
    "name": "Alongamento da panturrilha com toalha, sentado com as pernas esticadas",
    "place": "Sentado",
    "equip": "toalha",
    "desc": "Sentado com as pernas esticadas e uma toalha passada pela planta do pé, puxa a toalha trazendo os dedos em sua direção. Sustenta e relaxa.",
    "also": []
  },
  {
    "slug": "towel_soleus_roll",
    "path": "puppet/towel_soleus_roll.json",
    "name": "Alongamento do sóleo com toalha, joelho dobrado sobre um rolo",
    "place": "Sentado",
    "equip": "toalha · rolo",
    "desc": "Sentado, com o joelho levemente dobrado sobre um rolo e uma toalha passada pelo pé, puxa a toalha trazendo os dedos em sua direção. Sustenta e relaxa.",
    "also": []
  },
  {
    "slug": "towel_knee_flexion",
    "path": "puppet/towel_knee_flexion.json",
    "name": "Flexão do joelho assistida com toalha, deitado",
    "place": "Deitado",
    "equip": "toalha · colchonete",
    "desc": "Deitado de costas com uma toalha passada pelo pé, puxa a toalha deslizando o calcanhar em direção ao quadril e estica a perna de volta devagar.",
    "also": []
  },
  {
    "slug": "chair_pulley_flexion",
    "path": "puppet/chair_pulley_flexion.json",
    "name": "Flexão do ombro assistida com roldana, sentado",
    "place": "Sentado",
    "equip": "cadeira · roldana",
    "desc": "Sentado, com uma roldana acima e atrás, puxa a corda para baixo com o braço bom, deixando o outro braço subir à frente até onde for confortável.",
    "also": []
  }
],
  "lote14": [
  {
    "slug": "open_close_hand",
    "path": "hand/open_close_hand.json",
    "name": "Abrir e fechar a mão",
    "place": "Mão na mesa",
    "equip": "mesa",
    "desc": "Mão apoiada na mesa, palma para cima. Abre bem os dedos, afastando-os, depois fecha a mão sem força, com o polegar por cima dos dedos, e abre de novo.",
    "also": []
  },
  {
    "slug": "wrist_flexion_extension",
    "path": "hand/wrist_flexion_extension.json",
    "name": "Flexão e extensão de punho",
    "place": "Mão na mesa",
    "equip": "mesa",
    "desc": "Antebraço apoiado na mesa, palma para baixo e a mão além da borda. Dobra o punho para baixo, volta, leva a mão para cima e retorna devagar, com os dedos relaxados.",
    "also": []
  },
  {
    "slug": "forearm_pronation_supination",
    "path": "hand/forearm_pronation_supination.json",
    "name": "Pronação e supinação",
    "place": "Mão na mesa",
    "equip": "mesa",
    "desc": "Antebraço apoiado na mesa, polegar para cima. Gira a palma para baixo, volta ao polegar para cima e gira a palma para cima, sem mexer o cotovelo.",
    "also": []
  },
  {
    "slug": "thumb_opposition",
    "path": "hand/thumb_opposition.json",
    "name": "Oposição do polegar",
    "place": "Mão na mesa",
    "equip": "mesa",
    "desc": "Mão apoiada na mesa, palma para cima. Toca a ponta do polegar na ponta do indicador, do médio, do anelar e do mínimo, uma de cada vez, e abre a mão.",
    "also": []
  }
]
};
