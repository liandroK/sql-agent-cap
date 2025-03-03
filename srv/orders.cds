using { my.orders as my } from '../db/orders';

service OrderService {

    // Exposição da entidade Fornecedor
    @odata.draft.enabled: false
    entity fornecedores as
        projection on my.Fornecedor {
            ID,
            name,
            nif,
            email,
            telefone,
            ativo
        };

    // Exposição da entidade Order
    @odata.draft.enabled: false
    entity orders as
        projection on my.Order {
            ID,
            numero,
            data,
            valor_total,
            status,
            fornecedor
        };



    action order(orderID : UUID) returns String;

    action askAI(question: String) returns String;

    action askSQL(question: String) returns String;


}
