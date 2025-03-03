using {my.orders as my} from '../db/orders';

service OrderService {

    // Exposição da entidade Fornecedor
    @odata.draft.enabled: false
    entity fornecedores   as
        projection on my.Fornecedor {
            ID,
            name,
            nif,
            email,
            telefone,
            ativo
        };

    // Exposição da entidade Order, agora incluindo "materiais"
    @odata.draft.enabled: false
    entity orders         as
        projection on my.Order {
            ID,
            numero,
            data,
            valor_total,
            status,
            fornecedor,
            previsao_entrega,
            data_entrega,
            materiais // Adicionando a associação à entidade OrderMaterial
        };

    // Exposição da entidade Material
    @odata.draft.enabled: false
    entity materiais      as
        projection on my.Material {
            ID,
            codigo,
            descricao,
            unidade_medida,
            preco_unitario
        };

    // Exposição da relação entre Order e Material
    @odata.draft.enabled: false
    entity orderMateriais as
        projection on my.OrderMaterial {
            ID,
            order,
            material,
            quantidade,
            preco_unitario, // Agora exposto na API
            subtotal
        };

    // Ações personalizadas
    action order(orderID : UUID)     returns String;
    action askAI(question : String)  returns String;
    action askSQL(question : String) returns String;
}
